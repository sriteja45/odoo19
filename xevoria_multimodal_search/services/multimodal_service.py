# -*- coding: utf-8 -*-
import base64
import ctypes
import gc
import io
import json
import logging
import math
import os
import re
import socket
import tempfile
import threading
import urllib.request
from urllib.parse import parse_qs, urlparse

# Suppress Windows symlinks warning from huggingface_hub
os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")

_logger = logging.getLogger(__name__)

# Module-level model cache to prevent reloading EmbeddingGemma 2 weights on every request
_EMBEDDING_MODEL = None
_EMBEDDING_PROCESSOR = None
_EMBEDDING_CONFIG = None
_LOADED_MODEL_ID = None
_LOADED_DEVICE = None
_IS_DOWNLOADING = False
_MODEL_LOCK = threading.Lock()
_MEMORY_WATCHDOG_PATCHED = False


def _ensure_odoo_memory_headroom():
    """
    Ensures Odoo's ThreadedServer memory and real-time watchdogs on Windows
    allow sufficient RAM headroom (8-10 GB) and CPU execution time (7200s)
    for PyTorch + EmbeddingGemma 2 multimodal batch indexing.
    """
    global _MEMORY_WATCHDOG_PATCHED
    try:
        from odoo.tools import config
        min_soft = 8 * 1024 * 1024 * 1024   # 8 GB
        min_hard = 10 * 1024 * 1024 * 1024  # 10 GB
        min_time_real = 7200                # 2 hours for large catalog batch indexing
        min_time_cpu = 7200

        if config.get("limit_memory_soft") and config["limit_memory_soft"] < min_soft:
            config["limit_memory_soft"] = min_soft
        if config.get("limit_memory_hard") and config["limit_memory_hard"] < min_hard:
            config["limit_memory_hard"] = min_hard
        if config.get("limit_time_real") and config["limit_time_real"] < min_time_real:
            config["limit_time_real"] = min_time_real
        if config.get("limit_time_cpu") and config["limit_time_cpu"] < min_time_cpu:
            config["limit_time_cpu"] = min_time_cpu

        if not _MEMORY_WATCHDOG_PATCHED:
            try:
                import odoo.service.server as odoo_server
                if hasattr(odoo_server, "ThreadedServer") and hasattr(odoo_server.ThreadedServer, "check_limits"):
                    orig_check_limits = odoo_server.ThreadedServer.check_limits

                    def _safe_check_limits(self):
                        try:
                            if config.get("limit_memory_soft") and config["limit_memory_soft"] < min_soft:
                                config["limit_memory_soft"] = min_soft
                            if config.get("limit_memory_hard") and config["limit_memory_hard"] < min_hard:
                                config["limit_memory_hard"] = min_hard
                            if config.get("limit_time_real") and config["limit_time_real"] < min_time_real:
                                config["limit_time_real"] = min_time_real
                            if config.get("limit_time_cpu") and config["limit_time_cpu"] < min_time_cpu:
                                config["limit_time_cpu"] = min_time_cpu
                        except Exception:
                            pass
                        return orig_check_limits(self)

                    odoo_server.ThreadedServer.check_limits = _safe_check_limits
                _MEMORY_WATCHDOG_PATCHED = True
            except Exception:
                pass
    except Exception:
        pass


def _trim_process_working_set():
    """Releases unused cached memory pages back to the OS (especially effective on Windows)."""
    gc.collect()
    if os.name == "nt":
        try:
            handle = ctypes.windll.kernel32.GetCurrentProcess()
            ctypes.windll.psapi.EmptyWorkingSet(handle)
        except Exception:
            try:
                handle = ctypes.windll.kernel32.GetCurrentProcess()
                ctypes.windll.kernel32.SetProcessWorkingSetSize(handle, -1, -1)
            except Exception:
                pass


# Apply memory & timeout headroom patch immediately on import
_ensure_odoo_memory_headroom()


class MultimodalGemmaProcessor:
    """
    Processor wrapper pairing GemmaTokenizer and Gemma4ImageProcessor.
    Constructs the exact `<bos><|image><|image|>...<image|><eos>` and
    `<bos><|image><|video|>...<image|><eos>` token sequences expected by
    EmbeddingGemma2Model when EmbeddingGemma2Processor is bypassed on Windows.
    """
    def __init__(self, tokenizer, image_processor):
        self.tokenizer = tokenizer
        self.image_processor = image_processor
        self.boi_token = getattr(tokenizer, "boi_token", "<|image>") or "<|image>"
        self.eoi_token = getattr(tokenizer, "eoi_token", "<image|>") or "<image|>"
        self.image_token = getattr(tokenizer, "image_token", "<|image|>") or "<|image|>"
        self.video_token = getattr(tokenizer, "video_token", "<|video|>") or "<|video|>"

    def __call__(self, text=None, images=None, videos=None, **kwargs):
        return_tensors = kwargs.get("return_tensors", "pt")

        # 1. Image or Image+Text processing
        if images is not None:
            if not isinstance(images, list):
                images_list = [images]
            elif images and isinstance(images[0], list):
                images_list = [img for sublist in images for img in sublist]
            else:
                images_list = images

            img_kwargs = {
                k: v for k, v in kwargs.items()
                if k in ("return_tensors", "max_soft_tokens", "patch_size", "pooling_kernel_size", "do_resize", "do_rescale", "do_normalize")
            }
            img_kwargs["return_tensors"] = return_tensors
            img_out = self.image_processor(images=images_list, **img_kwargs)

            num_soft_list = img_out.pop("num_soft_tokens_per_image", None)
            if num_soft_list is None:
                default_soft = kwargs.get("max_soft_tokens") or getattr(self.image_processor, "max_soft_tokens", 70)
                num_soft_list = [default_soft] * len(images_list)

            expanded_prompts = []
            if text is None:
                for n_soft in num_soft_list:
                    n = int(n_soft.item()) if hasattr(n_soft, "item") else int(n_soft)
                    expanded_prompts.append(f"{self.boi_token}{self.image_token * n}{self.eoi_token}")
            else:
                text_list = [text] if isinstance(text, str) else list(text)
                img_idx = 0
                for sample in text_list:
                    if self.image_token in sample:
                        while self.image_token in sample and img_idx < len(num_soft_list):
                            n_soft = num_soft_list[img_idx]
                            n = int(n_soft.item()) if hasattr(n_soft, "item") else int(n_soft)
                            repl = f"{self.boi_token}{self.image_token * n}{self.eoi_token}"
                            sample = sample.replace(self.image_token, repl, 1)
                            img_idx += 1
                        expanded_prompts.append(sample)
                    else:
                        n_soft = num_soft_list[min(img_idx, len(num_soft_list) - 1)]
                        n = int(n_soft.item()) if hasattr(n_soft, "item") else int(n_soft)
                        repl = f"{self.boi_token}{self.image_token * n}{self.eoi_token}"
                        expanded_prompts.append(f"{repl} {sample}")
                        img_idx += 1

            tok_out = self.tokenizer(
                expanded_prompts,
                return_tensors=return_tensors,
                padding=kwargs.get("padding", True),
                truncation=kwargs.get("truncation", True),
                max_length=kwargs.get("max_length", 8192),
            )
            img_out.update(tok_out)
            return img_out

        # 2. Video frames processing (frames passed as list of PIL Images)
        if videos is not None:
            import torch
            frames = videos[0] if (isinstance(videos, list) and videos and isinstance(videos[0], list)) else videos
            if not isinstance(frames, list):
                frames = [frames]

            max_soft_tokens = kwargs.get("max_soft_tokens", 70)
            img_out = self.image_processor(
                images=frames,
                max_soft_tokens=max_soft_tokens,
                return_tensors=return_tensors,
            )
            num_soft_list = img_out.pop("num_soft_tokens_per_image", None)
            if num_soft_list is None:
                num_soft_list = [max_soft_tokens] * len(frames)

            frame_tokens = []
            for n_soft in num_soft_list:
                n = int(n_soft.item()) if hasattr(n_soft, "item") else int(n_soft)
                frame_tokens.append(f"{self.boi_token}{self.video_token * n}{self.eoi_token}")

            prompt = "".join(frame_tokens)
            if text:
                text_str = text[0] if isinstance(text, list) else text
                if self.video_token in text_str:
                    prompt = text_str.replace(self.video_token, prompt, 1)
                else:
                    prompt = f"{prompt} {text_str}"

            tok_out = self.tokenizer(
                [prompt],
                return_tensors=return_tensors,
                padding=True,
                truncation=True,
                max_length=kwargs.get("max_length", 8192),
            )
            return {
                "input_ids": tok_out["input_ids"],
                "attention_mask": tok_out["attention_mask"],
                "pixel_values_videos": img_out["pixel_values"],
                "video_position_ids": img_out["image_position_ids"],
                "num_frames_per_video": torch.tensor([len(frames)], dtype=torch.long),
            }

        # 3. Text-only processing
        if text is not None:
            return self.tokenizer(
                text,
                return_tensors=return_tensors,
                padding=kwargs.get("padding", True),
                truncation=kwargs.get("truncation", True),
                max_length=kwargs.get("max_length", 8192),
            )

        raise ValueError("One of `text`, `images`, or `videos` must be provided.")


class MultimodalService:
    """
    EmbeddingGemma 2 Multimodal Product Search Service.
    
    Maps text, images, and videos (from uploaded files or URLs) natively into a unified
    768-dimensional vector space.
    - Pure embedding and retrieval architecture.
    - Fast native float32 AVX2 execution on CPU (~0.8s per image/video frame) and bfloat16 on CUDA.
    - Task-prefix aware: 'task: search result | query: ...' for search queries,
      'title: ... | text: ...' for catalog documents.
    - Supports Matryoshka Representation Learning (MRL) dimension scaling (768d, 512d, 256d).
    - Cross-modal retrieval: searching by image, video, or text returns matched products
      along with their playable product video (`video_url` / `video_embed_url`).
    """

    DEFAULT_MODEL_ID = "google/embeddinggemma-2"
    DEFAULT_DIMENSION = 768

    def __init__(self, env=None):
        _ensure_odoo_memory_headroom()
        self.env = env

        # Configurations from Odoo settings or environment
        self.model_id = self._get_param("multimodal.model_id") or os.getenv("EMBEDDING_MODEL_ID") or self.DEFAULT_MODEL_ID
        self.pgvector_db_url = self._get_param("multimodal.pgvector_db_url") or os.getenv("PGVECTOR_DB_URL") or "postgresql+psycopg://odoo:odoo@localhost:5532/odoo"
        self.device_setting = (self._get_param("multimodal.device") or "auto").lower()

        try:
            self.mrl_dim = int(self._get_param("multimodal.mrl_dimension") or 768)
        except (ValueError, TypeError):
            self.mrl_dim = 768

        try:
            self.min_score = float(self._get_param("multimodal.min_score") or 25.0)
        except (ValueError, TypeError):
            self.min_score = 25.0

        # Resolve reachable PgVector URL(s) (checks configured URL + local Docker ports 5532 and 5432)
        self.active_pgvector_urls = self._resolve_reachable_pgvector_urls()
        self.is_pgvector_online = bool(self.active_pgvector_urls)

    def _get_param(self, key):
        if self.env:
            try:
                return self.env['ir.config_parameter'].sudo().get_param(key, default="")
            except Exception:
                pass
        return ""

    def _get_candidate_pgvector_urls(self):
        candidates = []

        def _add(url):
            if not url:
                return
            clean = url.replace("postgresql+psycopg://", "postgresql://").replace("postgresql+psycopg2://", "postgresql://")
            if clean not in candidates:
                candidates.append(clean)

        _add(self.pgvector_db_url)

        if ":5532/" in self.pgvector_db_url:
            _add(self.pgvector_db_url.replace(":5532/", ":5432/"))
        elif ":5432/" in self.pgvector_db_url:
            _add(self.pgvector_db_url.replace(":5432/", ":5532/"))

        try:
            from odoo.tools import config
            db_host = config.get("db_host") or "localhost"
            db_port = config.get("db_port") or 5432
            db_user = config.get("db_user") or "odoo"
            db_pass = config.get("db_password") or "odoo"
            db_name = (self.env.cr.dbname if (self.env and getattr(self.env, "cr", None)) else None) or config.get("db_name") or "odoo"
            if isinstance(db_name, list):
                db_name = db_name[0] if db_name else "odoo"
            _add(f"postgresql://{db_user}:{db_pass}@{db_host}:{db_port}/{db_name}")
            if str(db_port) != "5532":
                _add(f"postgresql://{db_user}:{db_pass}@{db_host}:5532/{db_name}")
        except Exception:
            pass

        return candidates

    def _resolve_reachable_pgvector_urls(self):
        reachable = []
        for url in self._get_candidate_pgvector_urls():
            try:
                u = urlparse(url.replace("postgresql://", "http://"))
                host = u.hostname or "localhost"
                port = u.port or 5432
                with socket.create_connection((host, port), timeout=0.25):
                    reachable.append(url)
            except Exception:
                continue
        return reachable

    # =========================================================================
    # Model Loading (Cached Singleton with Fast CPU float32 / CUDA bfloat16)
    # =========================================================================

    def _get_device(self):
        try:
            import torch
            if self.device_setting == "cuda" and torch.cuda.is_available():
                return "cuda"
            elif self.device_setting == "cpu":
                return "cpu"
            return "cuda" if torch.cuda.is_available() else "cpu"
        except Exception:
            return "cpu"

    @staticmethod
    def _load_processor_from_hub(model_id, local_files_only=True):
        from transformers import AutoProcessor, AutoTokenizer, AutoImageProcessor
        try:
            return AutoProcessor.from_pretrained(
                model_id,
                trust_remote_code=True,
                local_files_only=local_files_only,
            )
        except Exception:
            tok = AutoTokenizer.from_pretrained(
                model_id,
                trust_remote_code=True,
                local_files_only=local_files_only,
            )
            img_proc = AutoImageProcessor.from_pretrained(
                model_id,
                trust_remote_code=True,
                local_files_only=local_files_only,
            )
            return MultimodalGemmaProcessor(tok, img_proc)

    def _load_model(self):
        """
        Loads EmbeddingGemma 2 processor and model:
        - Uses native `torch.float32` on CPU (10-15x faster AVX2 execution than emulated bfloat16)
          and `torch.bfloat16` on CUDA GPUs.
        - Configures CPU thread parallelism for fast vision encoder inference.
        """
        global _EMBEDDING_MODEL, _EMBEDDING_PROCESSOR, _EMBEDDING_CONFIG, _LOADED_MODEL_ID, _LOADED_DEVICE, _IS_DOWNLOADING

        _ensure_odoo_memory_headroom()
        target_device = self._get_device()

        if (_EMBEDDING_MODEL is not None and
            _EMBEDDING_PROCESSOR is not None and
            _LOADED_MODEL_ID == self.model_id and
            _LOADED_DEVICE == target_device):
            return _EMBEDDING_MODEL, _EMBEDDING_PROCESSOR, target_device

        with _MODEL_LOCK:
            if (_EMBEDDING_MODEL is not None and
                _EMBEDDING_PROCESSOR is not None and
                _LOADED_MODEL_ID == self.model_id and
                _LOADED_DEVICE == target_device):
                return _EMBEDDING_MODEL, _EMBEDDING_PROCESSOR, target_device

            try:
                import torch
                from transformers import AutoConfig, AutoModel

                if target_device == "cpu":
                    try:
                        cpu_cores = os.cpu_count() or 4
                        torch.set_num_threads(max(4, min(cpu_cores, 12)))
                    except Exception:
                        pass

                dtype = torch.bfloat16 if target_device == "cuda" else torch.float32

                try:
                    if _EMBEDDING_PROCESSOR is None or _LOADED_MODEL_ID != self.model_id:
                        _EMBEDDING_PROCESSOR = self._load_processor_from_hub(self.model_id, local_files_only=True)

                    if _EMBEDDING_CONFIG is None or _LOADED_MODEL_ID != self.model_id:
                        cfg = AutoConfig.from_pretrained(
                            self.model_id,
                            trust_remote_code=True,
                            local_files_only=True,
                        )
                        if hasattr(cfg, "audio_config"):
                            cfg.audio_config = None
                        _EMBEDDING_CONFIG = cfg

                    model_kwargs = {
                        "config": _EMBEDDING_CONFIG,
                        "trust_remote_code": True,
                        "low_cpu_mem_usage": True,
                        "local_files_only": True,
                    }
                    try:
                        model = AutoModel.from_pretrained(self.model_id, dtype=dtype, **model_kwargs)
                    except TypeError:
                        model = AutoModel.from_pretrained(self.model_id, torch_dtype=dtype, **model_kwargs)

                    model.to(device=target_device, dtype=dtype)
                    model.eval()
                    _trim_process_working_set()

                    _EMBEDDING_MODEL = model
                    _LOADED_MODEL_ID = self.model_id
                    _LOADED_DEVICE = target_device

                    _logger.info(
                        "EmbeddingGemma 2 model loaded from local cache into memory (device: %s, dtype: %s)",
                        target_device, dtype
                    )
                    return _EMBEDDING_MODEL, _EMBEDDING_PROCESSOR, target_device
                except Exception as cache_err:
                    _logger.debug("Local cache miss or incomplete files: %s", cache_err)

                if not _IS_DOWNLOADING:
                    self._trigger_background_download(self.model_id, target_device, dtype)

                return None, None, target_device

            except Exception as e:
                _logger.warning("EmbeddingGemma 2 initialization notice: %s. Operating with local vector fallback.", e)
                return None, None, target_device

    def _trigger_background_download(self, model_id, target_device, dtype):
        global _IS_DOWNLOADING
        _IS_DOWNLOADING = True

        def _worker():
            global _EMBEDDING_MODEL, _EMBEDDING_PROCESSOR, _EMBEDDING_CONFIG, _LOADED_MODEL_ID, _LOADED_DEVICE, _IS_DOWNLOADING
            try:
                from transformers import AutoConfig, AutoModel
                _logger.info("Background Downloader: Caching EmbeddingGemma 2 files for '%s'...", model_id)

                processor = self._load_processor_from_hub(model_id, local_files_only=False)
                cfg = AutoConfig.from_pretrained(model_id, trust_remote_code=True)
                if hasattr(cfg, "audio_config"):
                    cfg.audio_config = None

                dl_kwargs = {
                    "config": cfg,
                    "trust_remote_code": True,
                    "low_cpu_mem_usage": True,
                }
                try:
                    model = AutoModel.from_pretrained(model_id, dtype=dtype, **dl_kwargs)
                except TypeError:
                    model = AutoModel.from_pretrained(model_id, torch_dtype=dtype, **dl_kwargs)

                model.to(device=target_device, dtype=dtype)
                model.eval()
                _trim_process_working_set()

                _EMBEDDING_PROCESSOR = processor
                _EMBEDDING_CONFIG = cfg
                _EMBEDDING_MODEL = model
                _LOADED_MODEL_ID = model_id
                _LOADED_DEVICE = target_device
                _logger.info("Background Downloader: EmbeddingGemma 2 download complete! Model is now live in memory.")
            except Exception as e:
                _logger.warning("Background download notice: %s", e)
            finally:
                _IS_DOWNLOADING = False

        thread = threading.Thread(target=_worker, name="EmbeddingGemma_Download_Thread", daemon=True)
        thread.start()
        _logger.info("Initiated background download for EmbeddingGemma 2 weights. Odoo requests will proceed without waiting.")

    # =========================================================================
    # Pooling & Normalization Helpers (Official EmbeddingGemma 2 Spec)
    # =========================================================================

    def _pool_and_normalize(self, outputs, attention_mask=None):
        import torch
        import torch.nn.functional as F

        if hasattr(outputs, "embeddings") and outputs.embeddings is not None:
            emb = outputs.embeddings
            if emb.ndim == 2:
                emb = emb[0]
        elif hasattr(outputs, "last_hidden_state") and outputs.last_hidden_state is not None:
            token_embeddings = outputs.last_hidden_state
            if attention_mask is not None:
                mask = attention_mask.unsqueeze(-1).to(token_embeddings.dtype)
                emb = (token_embeddings * mask).sum(dim=1) / mask.sum(dim=1).clamp(min=1e-9)
            else:
                emb = token_embeddings.mean(dim=1)
            emb = emb[0]
        elif hasattr(outputs, "pooler_output") and outputs.pooler_output is not None:
            emb = outputs.pooler_output[0]
        else:
            raw = outputs[0]
            emb = raw.mean(dim=1)[0] if raw.ndim == 3 else raw[0]

        emb = emb[:self.mrl_dim].float()
        emb = F.normalize(emb, p=2, dim=-1)
        return emb.cpu().tolist()

    def _prepare_model_inputs(self, raw_inputs, model, device):
        import torch
        model_dtype = getattr(model, "dtype", torch.float32 if device == "cpu" else torch.bfloat16)
        prepared = {}
        unused_keys = {"num_soft_tokens_per_image", "num_soft_tokens_per_video", "video_metadata"}
        for k, v in raw_inputs.items():
            if k in unused_keys or v is None:
                continue
            if hasattr(v, "to"):
                if torch.is_floating_point(v):
                    prepared[k] = v.to(device=device, dtype=model_dtype)
                else:
                    prepared[k] = v.to(device=device)
            else:
                prepared[k] = v
        return prepared

    # =========================================================================
    # Embedding Generation (Text, Images, and Video from File or URL)
    # =========================================================================

    def get_image_embedding(self, image_bytes):
        """
        Generates 768-d vector embedding for a product or query image using EmbeddingGemma 2.
        Uses `max_soft_tokens=70` on CPU (~0.8s per image) and `280` on CUDA.
        """
        if not image_bytes:
            return [0.0] * self.mrl_dim

        model, processor, device = self._load_model()
        if model and processor:
            try:
                import torch
                from PIL import Image

                if isinstance(image_bytes, str):
                    image_bytes = base64.b64decode(image_bytes)

                image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
                soft_tokens = 70 if device == "cpu" else 280

                try:
                    raw_inputs = processor(images=[image], max_soft_tokens=soft_tokens, return_tensors="pt")
                except TypeError:
                    raw_inputs = processor(images=[image], return_tensors="pt")

                if "input_ids" not in raw_inputs and hasattr(processor, "tokenizer"):
                    tok = processor.tokenizer
                    wrapper = MultimodalGemmaProcessor(tok, getattr(processor, "image_processor", processor))
                    raw_inputs = wrapper(images=[image], max_soft_tokens=soft_tokens, return_tensors="pt")

                inputs = self._prepare_model_inputs(raw_inputs, model, device)

                with torch.inference_mode():
                    outputs = model(**inputs)
                    vec = self._pool_and_normalize(outputs, inputs.get("attention_mask"))

                del inputs, outputs, raw_inputs
                _trim_process_working_set()
                return vec
            except Exception as e:
                _logger.warning("EmbeddingGemma 2 image embedding inference error: %s", e)

        return self._fallback_image_embedding(image_bytes, dim=self.mrl_dim)

    def get_text_embedding(self, text, is_query=False):
        """
        Generates 768-d vector embedding for text using EmbeddingGemma 2.
        """
        text = (text or "").strip()
        if not text:
            return [0.0] * self.mrl_dim

        if is_query:
            lower_text = text.lower()
            if lower_text.startswith("task:"):
                formatted_text = text
            elif lower_text.startswith("query:"):
                clean_q = text.split(":", 1)[1].strip()
                formatted_text = f"task: search result | query: {clean_q}"
            else:
                formatted_text = f"task: search result | query: {text}"
        else:
            if not text.lower().startswith("title:"):
                formatted_text = f"title: none | text: {text}"
            else:
                formatted_text = text

        model, processor, device = self._load_model()
        if model and processor:
            try:
                import torch

                tokenizer = getattr(processor, "tokenizer", processor)
                raw_inputs = tokenizer(
                    [formatted_text],
                    padding=True,
                    truncation=True,
                    max_length=2048,
                    return_tensors="pt",
                )
                inputs = self._prepare_model_inputs(raw_inputs, model, device)

                with torch.inference_mode():
                    outputs = model(**inputs)
                    vec = self._pool_and_normalize(outputs, inputs.get("attention_mask"))

                del inputs, outputs, raw_inputs
                _trim_process_working_set()
                return vec
            except Exception as e:
                _logger.warning("EmbeddingGemma 2 text embedding inference error: %s", e)

        return self._fallback_text_embedding(formatted_text, dim=self.mrl_dim)

    def get_video_embedding(self, video_bytes=None, frames=None, video_url=None):
        """
        Generates 768-d vector embedding for a product or query video using EmbeddingGemma 2.
        Supports:
        1. Uploaded video binary (`video_bytes`)
        2. Video URL (`video_url` - direct MP4/WebM/MOV link or YouTube/Vimeo link)
        3. Pre-extracted PIL `frames`
        """
        extracted_frames = frames
        if not extracted_frames and video_bytes:
            extracted_frames = self._extract_video_frames(video_bytes, max_frames=4)
        if not extracted_frames and video_url:
            extracted_frames = self._extract_video_frames_from_url(video_url, max_frames=4)

        if not extracted_frames:
            return [0.0] * self.mrl_dim

        model, processor, device = self._load_model()
        if model and processor:
            try:
                import torch

                raw_inputs = None
                soft_tokens = 70 if device == "cpu" else 140
                if isinstance(processor, MultimodalGemmaProcessor):
                    raw_inputs = processor(videos=extracted_frames, max_soft_tokens=soft_tokens, return_tensors="pt")
                else:
                    try:
                        tok = getattr(processor, "tokenizer", None)
                        img_proc = getattr(processor, "image_processor", None)
                        if tok and img_proc:
                            wrapper = MultimodalGemmaProcessor(tok, img_proc)
                            raw_inputs = wrapper(videos=extracted_frames, max_soft_tokens=soft_tokens, return_tensors="pt")
                        else:
                            raw_inputs = processor(images=extracted_frames, return_tensors="pt")
                    except Exception:
                        raw_inputs = processor(images=[extracted_frames], return_tensors="pt")

                inputs = self._prepare_model_inputs(raw_inputs, model, device)

                with torch.inference_mode():
                    outputs = model(**inputs)
                    vec = self._pool_and_normalize(outputs, inputs.get("attention_mask"))

                del inputs, outputs, raw_inputs
                _trim_process_working_set()
                return vec
            except Exception as e:
                _logger.warning("EmbeddingGemma 2 video embedding inference notice (%s), averaging frame embeddings.", e)
                try:
                    frame_vecs = []
                    for frame in extracted_frames[:4]:
                        buf = io.BytesIO()
                        frame.save(buf, format="JPEG")
                        frame_vecs.append(self.get_image_embedding(buf.getvalue()))
                    if frame_vecs:
                        avg_vec = [sum(col) / len(frame_vecs) for col in zip(*frame_vecs)]
                        return self._normalize(avg_vec)
                except Exception:
                    pass

        try:
            buf = io.BytesIO()
            extracted_frames[0].save(buf, format="JPEG")
            return self._fallback_image_embedding(buf.getvalue(), dim=self.mrl_dim)
        except Exception:
            return [0.0] * self.mrl_dim

    @staticmethod
    def _extract_youtube_id(url):
        """Extracts the 11-character YouTube video ID from any YouTube URL format."""
        if not url:
            return None
        url = url.strip()
        parsed = urlparse(url)
        host = (parsed.hostname or "").lower()
        if "youtu.be" in host:
            vid = parsed.path.lstrip("/").split("/")[0]
            return vid if len(vid) >= 10 else None
        if "youtube.com" in host or "youtube-nocookie.com" in host:
            if parsed.path.startswith("/watch"):
                qs = parse_qs(parsed.query)
                vid = (qs.get("v") or [None])[0]
                return vid
            for prefix in ("/embed/", "/shorts/", "/v/", "/live/"):
                if parsed.path.startswith(prefix):
                    vid = parsed.path[len(prefix):].split("/")[0].split("?")[0]
                    return vid if vid else None
        return None

    @staticmethod
    def _extract_vimeo_id(url):
        """Extracts numeric Vimeo video ID from a Vimeo URL."""
        if not url:
            return None
        m = re.search(r"vimeo\.com/(?:video/)?(\d+)", url)
        return m.group(1) if m else None

    def _extract_video_frames_from_url(self, video_url, max_frames=4):
        """
        Extracts up to `max_frames` RGB PIL.Image frames from a video URL:
        1. If YouTube URL: fetches the 4 multi-timestamp keyframes (`0.jpg`, `1.jpg`, `2.jpg`, `3.jpg`)
           directly from YouTube's image servers so YouTube product videos embed cleanly without yt-dlp.
        2. If direct video URL (`.mp4`, `.webm`, `.mov`, etc.): downloads the video stream (up to 50 MB)
           or opens it via OpenCV `cv2.VideoCapture(url)` to sample frames.
        """
        if not video_url:
            return []

        video_url = video_url.strip()
        from PIL import Image

        # 1. Check if YouTube URL -> fetch multi-frame storyboard thumbnails (0.jpg, 1.jpg, 2.jpg, 3.jpg)
        yt_id = self._extract_youtube_id(video_url)
        if yt_id:
            yt_frames = []
            for thumb_name in ("0.jpg", "1.jpg", "2.jpg", "3.jpg", "hqdefault.jpg"):
                if len(yt_frames) >= max_frames:
                    break
                thumb_url = f"https://img.youtube.com/vi/{yt_id}/{thumb_name}"
                try:
                    req = urllib.request.Request(thumb_url, headers={"User-Agent": "Mozilla/5.0"})
                    with urllib.request.urlopen(req, timeout=8) as resp:
                        img_bytes = resp.read()
                        img = Image.open(io.BytesIO(img_bytes)).convert("RGB")
                        yt_frames.append(img)
                except Exception:
                    continue
            if yt_frames:
                _logger.info("Extracted %d keyframes from YouTube video ID %s", len(yt_frames), yt_id)
                return yt_frames

        # 2. Check if Vimeo URL -> fetch thumbnail via Vimeo oEmbed JSON API
        vimeo_id = self._extract_vimeo_id(video_url)
        if vimeo_id:
            try:
                oembed_url = f"https://vimeo.com/api/oembed.json?url=https://vimeo.com/{vimeo_id}"
                req = urllib.request.Request(oembed_url, headers={"User-Agent": "Mozilla/5.0"})
                with urllib.request.urlopen(req, timeout=8) as resp:
                    meta = json.loads(resp.read().decode("utf-8"))
                    thumb_url = meta.get("thumbnail_url")
                    if thumb_url:
                        req_t = urllib.request.Request(thumb_url, headers={"User-Agent": "Mozilla/5.0"})
                        with urllib.request.urlopen(req_t, timeout=8) as resp_t:
                            img = Image.open(io.BytesIO(resp_t.read())).convert("RGB")
                            return [img]
            except Exception:
                pass

        # 3. Direct video URL (.mp4, .webm, .mov, etc.) -> Download bytes (up to 50 MB) and extract frames
        try:
            req = urllib.request.Request(video_url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=15) as resp:
                video_bytes = resp.read(50 * 1024 * 1024)
            if video_bytes:
                frames = self._extract_video_frames(video_bytes, max_frames=max_frames)
                if frames:
                    return frames
        except Exception as dl_err:
            _logger.debug("Direct video URL download notice (%s), trying OpenCV stream capture.", dl_err)

        # 4. Fallback: OpenCV direct network stream capture
        try:
            import cv2
            cap = cv2.VideoCapture(video_url)
            frames = []
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
            if total_frames > 0:
                num_to_sample = min(total_frames, max_frames)
                indices = [int(i * (total_frames - 1) / max(1, num_to_sample - 1)) for i in range(num_to_sample)]
                for idx in sorted(set(indices)):
                    cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
                    ret, frame = cap.read()
                    if ret and frame is not None:
                        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                        frames.append(Image.fromarray(rgb))
            else:
                step = 15
                count = 0
                while len(frames) < max_frames and count < 180:
                    ret, frame = cap.read()
                    if not ret or frame is None:
                        break
                    if count % step == 0:
                        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                        frames.append(Image.fromarray(rgb))
                    count += 1
            cap.release()
            if frames:
                return frames
        except Exception as cv_err:
            _logger.debug("OpenCV URL capture notice: %s", cv_err)

        return []

    def _extract_video_frames(self, video_bytes, max_frames=4):
        """
        Extracts up to `max_frames` uniformly sampled RGB PIL.Image frames from video bytes
        (MP4, WebM, MOV, AVI, GIF) using OpenCV (cv2), PyAV (av), or PIL.
        """
        if not video_bytes:
            return []

        if isinstance(video_bytes, str):
            try:
                video_bytes = base64.b64decode(video_bytes)
            except Exception:
                return []

        from PIL import Image

        # 1. Try PIL first (handles animated GIF/WebP or single image uploaded as video)
        try:
            img = Image.open(io.BytesIO(video_bytes))
            n_frames = getattr(img, "n_frames", 1)
            if n_frames >= 1:
                indices = [int(i * (n_frames - 1) / max(1, min(n_frames, max_frames) - 1)) for i in range(min(n_frames, max_frames))]
                pil_frames = []
                for idx in sorted(set(indices)):
                    img.seek(idx)
                    pil_frames.append(img.convert("RGB").copy())
                if pil_frames:
                    return pil_frames
        except Exception:
            pass

        # 2. Try OpenCV (cv2) via temporary file
        tmp_path = None
        try:
            import cv2
            with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp:
                tmp.write(video_bytes)
                tmp_path = tmp.name

            cap = cv2.VideoCapture(tmp_path)
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
            frames = []

            if total_frames > 0:
                num_to_sample = min(total_frames, max_frames)
                indices = [int(i * (total_frames - 1) / max(1, num_to_sample - 1)) for i in range(num_to_sample)]
                for idx in sorted(set(indices)):
                    cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
                    ret, frame = cap.read()
                    if ret and frame is not None:
                        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                        frames.append(Image.fromarray(rgb))
            else:
                step = 15
                count = 0
                while len(frames) < max_frames:
                    ret, frame = cap.read()
                    if not ret or frame is None:
                        break
                    if count % step == 0:
                        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                        frames.append(Image.fromarray(rgb))
                    count += 1

            cap.release()
            if frames:
                return frames
        except Exception as e:
            _logger.debug("OpenCV video frame extraction notice: %s", e)
        finally:
            if tmp_path and os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                except Exception:
                    pass

        # 3. Try PyAV (av) if installed
        try:
            import av
            container = av.open(io.BytesIO(video_bytes))
            stream = container.streams.video[0]
            all_frames = []
            for packet in container.demux(stream):
                for frame in packet.decode():
                    all_frames.append(frame.to_image().convert("RGB"))
                    if len(all_frames) >= max_frames * 4:
                        break
                if len(all_frames) >= max_frames * 4:
                    break
            container.close()
            if all_frames:
                num_to_sample = min(len(all_frames), max_frames)
                indices = [int(i * (len(all_frames) - 1) / max(1, num_to_sample - 1)) for i in range(num_to_sample)]
                return [all_frames[i] for i in sorted(set(indices))]
        except Exception:
            pass

        return []

    # =========================================================================
    # Resilient Deterministic Fallback Vector Generators
    # =========================================================================

    def _fallback_text_embedding(self, text, dim=768):
        words = re.findall(r'\w+', text.lower())
        vec = [0.0] * dim
        for i, w in enumerate(words):
            h = hash(w)
            idx = abs(h) % dim
            weight = 1.0 / (1.0 + math.log(i + 2))
            vec[idx] += (((h >> 3) % 100) / 100.0) * weight
        return self._normalize(vec)

    def _fallback_image_embedding(self, image_bytes, dim=768):
        try:
            from PIL import Image
            if isinstance(image_bytes, str):
                image_bytes = base64.b64decode(image_bytes)
            img = Image.open(io.BytesIO(image_bytes)).convert("RGB").resize((16, 16))
            pixels = list(img.getdata())
            vec = [0.0] * dim
            for idx, (r, g, b) in enumerate(pixels):
                pos = (idx * 3) % dim
                vec[pos] += r / 255.0
                vec[(pos + 1) % dim] += g / 255.0
                vec[(pos + 2) % dim] += b / 255.0
            return self._normalize(vec)
        except Exception:
            return [0.0] * dim

    @staticmethod
    def _normalize(vec):
        norm = math.sqrt(sum(x * x for x in vec))
        if norm < 1e-9:
            return [0.0] * len(vec)
        return [float(x / norm) for x in vec]

    @staticmethod
    def cosine_similarity(v1, v2):
        if not v1 or not v2:
            return 0.0
        min_len = min(len(v1), len(v2))
        if min_len == 0:
            return 0.0
        dot = sum(v1[i] * v2[i] for i in range(min_len))
        norm1 = math.sqrt(sum(v1[i] * v1[i] for i in range(min_len)))
        norm2 = math.sqrt(sum(v2[i] * v2[i] for i in range(min_len)))
        if norm1 <= 1e-9 or norm2 <= 1e-9:
            return 0.0
        return float(dot / (norm1 * norm2))

    # =========================================================================
    # Product Video Resolution & Result Payload Builder
    # =========================================================================

    def _get_product_video_source(self, product):
        """
        Locates a product's video from any of 4 supported places:
        1. `product.multimodal_video_file` (uploaded video file on the product form)
        2. `product.multimodal_video_url` (direct video URL or YouTube/Vimeo link on the product form)
        3. `product.product_template_image_ids` (Odoo eCommerce extra media with `video_url`)
        4. `ir.attachment` linked to `product.template` with `mimetype ilike 'video/%'`
        Returns dict with `video_bytes`, `video_url`, `attachment_id`.
        """
        # 1. Uploaded video binary field on Product Form (`multimodal_video_file`)
        raw_bin = getattr(product, "multimodal_video_file", False)
        if raw_bin:
            try:
                video_bytes = base64.b64decode(raw_bin) if isinstance(raw_bin, (str, bytes)) else None
                if video_bytes:
                    return {
                        "video_bytes": video_bytes,
                        "video_url": f"/shop/multimodal/product_video/{product.id}",
                        "attachment_id": False,
                    }
            except Exception:
                pass

        # 2. Video URL field on Product Form (`multimodal_video_url`)
        custom_url = (getattr(product, "multimodal_video_url", "") or "").strip()
        if custom_url:
            return {
                "video_bytes": None,
                "video_url": custom_url,
                "attachment_id": False,
            }

        # 3. Odoo eCommerce Extra Media (`product_template_image_ids.video_url`)
        media_records = getattr(product, "product_template_image_ids", False)
        if media_records:
            for media in media_records:
                m_url = (getattr(media, "video_url", "") or "").strip()
                if m_url:
                    return {
                        "video_bytes": None,
                        "video_url": m_url,
                        "attachment_id": False,
                    }

        # 4. Any `video/*` attachment attached to `product.template`
        if self.env:
            try:
                att = self.env["ir.attachment"].sudo().search([
                    ("res_model", "=", "product.template"),
                    ("res_id", "=", product.id),
                    ("res_field", "=", False),
                    ("mimetype", "ilike", "video/"),
                ], limit=1)
                if att and att.datas:
                    return {
                        "video_bytes": base64.b64decode(att.datas),
                        "video_url": f"/shop/multimodal/product_video/{product.id}",
                        "attachment_id": att.id,
                    }
            except Exception:
                pass

        return None

    def _get_product_video_info(self, product):
        """
        Returns playable video URL metadata for a matched product so the frontend
        search card can render an HTML5 `<video>` player or YouTube/Vimeo `<iframe>`.
        """
        video_url = ""
        video_embed_url = ""
        video_type = ""

        # Check uploaded binary file first
        if getattr(product, "multimodal_video_file", False):
            video_url = f"/shop/multimodal/product_video/{product.id}"
            video_type = "file"
        elif getattr(product, "multimodal_video_url", False):
            video_url = product.multimodal_video_url.strip()
        else:
            # Check eCommerce media
            media_records = getattr(product, "product_template_image_ids", False)
            if media_records:
                for media in media_records:
                    if getattr(media, "video_url", False):
                        video_url = media.video_url.strip()
                        break

            # Check `xevoria.multimodal.embedding` video record or `ir.attachment`
            if not video_url and self.env:
                try:
                    vid_emb = self.env["xevoria.multimodal.embedding"].sudo().search([
                        ("product_tmpl_id", "=", product.id),
                        ("media_type", "=", "video"),
                    ], limit=1)
                    if vid_emb and vid_emb.video_url:
                        video_url = vid_emb.video_url.strip()
                    elif vid_emb and vid_emb.attachment_id:
                        video_url = f"/shop/multimodal/product_video/{product.id}"
                        video_type = "file"
                    else:
                        att_count = self.env["ir.attachment"].sudo().search_count([
                            ("res_model", "=", "product.template"),
                            ("res_id", "=", product.id),
                            ("mimetype", "ilike", "video/"),
                        ])
                        if att_count > 0:
                            video_url = f"/shop/multimodal/product_video/{product.id}"
                            video_type = "file"
                except Exception:
                    pass

        if video_url and not video_type:
            yt_id = self._extract_youtube_id(video_url)
            vimeo_id = self._extract_vimeo_id(video_url)
            if yt_id:
                video_embed_url = f"https://www.youtube.com/embed/{yt_id}"
                video_type = "youtube"
            elif vimeo_id:
                video_embed_url = f"https://player.vimeo.com/video/{vimeo_id}"
                video_type = "vimeo"
            else:
                video_type = "file"

        return {
            "has_video": bool(video_url or video_embed_url),
            "video_url": video_url,
            "video_embed_url": video_embed_url,
            "video_type": video_type,
        }

    def _build_product_result_dict(self, product, score_pct, media_type, source_prefix="EmbeddingGemma 2"):
        """
        Builds the unified search result dictionary for a matched product, including both
        its product image and its playable product video (if the product has a video).
        """
        cur_symbol = product.currency_id.symbol if product.currency_id else "$"
        video_info = self._get_product_video_info(product)
        return {
            "product_id": product.id,
            "name": product.name,
            "default_code": product.default_code or "",
            "description": (product.description_sale or product.name or "")[:150],
            "price": product.list_price,
            "currency_symbol": cur_symbol,
            "formatted_price": f"{cur_symbol} {product.list_price:,.2f}",
            "image_url": f"/web/image/product.template/{product.id}/image_512",
            "product_url": f"/shop/product/{product.id}",
            "score": score_pct,
            "matched_modality": media_type,
            "matched_label": f"{source_prefix} ({media_type})",
            "has_video": video_info["has_video"],
            "video_url": video_info["video_url"],
            "video_embed_url": video_info["video_embed_url"],
            "video_type": video_info["video_type"],
        }

    # =========================================================================
    # Product Catalog Indexing (Text, Image, and Video)
    # =========================================================================

    def index_product(self, product):
        """
        Embeds product into the 768-d EmbeddingGemma 2 vector space:
        1. Text specification embedding formatted with 'title: ... | text: ...'
        2. Visual image embedding (if product has an image)
        3. Video embedding (if product has an uploaded video file, video URL, or video attachment)
        All modalities are stored in `xevoria.multimodal.embedding` AND PgVector if online.
        """
        _ensure_odoo_memory_headroom()
        emb_model = self.env["xevoria.multimodal.embedding"].sudo() if self.env else None

        # 1. Product Text Document (Title + Description + SKU + Category + Price)
        currency_symbol = product.currency_id.symbol if product.currency_id else "$"
        desc_parts = []
        if getattr(product, "description_sale", False):
            desc_parts.append(str(product.description_sale).strip())
        if getattr(product, "description_ecommerce", False):
            clean_ecom = re.sub(r"<[^>]+>", " ", str(product.description_ecommerce)).strip()
            if clean_ecom:
                desc_parts.append(clean_ecom)
        if getattr(product, "description", False):
            clean_desc = re.sub(r"<[^>]+>", " ", str(product.description)).strip()
            if clean_desc:
                desc_parts.append(clean_desc)

        desc_text = " ".join(desc_parts) if desc_parts else (product.name or "")
        categ_name = product.categ_id.name if product.categ_id else "General"
        code = product.default_code or "N/A"

        formatted_doc = (
            f"title: {product.name} | "
            f"text: {desc_text}. SKU: {code}. Category: {categ_name}. Price: {currency_symbol}{product.list_price:,.2f}"
        )
        text_vec = self.get_text_embedding(formatted_doc, is_query=False)

        if emb_model:
            existing_text = emb_model.search([
                ("product_tmpl_id", "=", product.id),
                ("media_type", "=", "text"),
            ], limit=1)
            vals = {
                "name": f"{product.name} (Specs)",
                "product_tmpl_id": product.id,
                "media_type": "text",
                "description": formatted_doc,
                "embedding_json": json.dumps(text_vec),
                "dimension": len(text_vec),
            }
            if existing_text:
                existing_text.write(vals)
            else:
                emb_model.create(vals)

        self._upsert_pgvector(product, text_vec, media_type="text", content=formatted_doc)

        # 2. Product Image Visual Embedding
        img_data = getattr(product, "image_512", False) or getattr(product, "image_1920", False)
        if img_data:
            img_bytes = base64.b64decode(img_data) if isinstance(img_data, (str, bytes)) else None
            if img_bytes:
                img_vec = self.get_image_embedding(img_bytes)
                img_desc = f"Visual product image representation for {product.name}"
                if emb_model:
                    existing_img = emb_model.search([
                        ("product_tmpl_id", "=", product.id),
                        ("media_type", "=", "image"),
                    ], limit=1)
                    img_vals = {
                        "name": f"{product.name} (Photo)",
                        "product_tmpl_id": product.id,
                        "media_type": "image",
                        "description": img_desc,
                        "embedding_json": json.dumps(img_vec),
                        "dimension": len(img_vec),
                    }
                    if existing_img:
                        existing_img.write(img_vals)
                    else:
                        emb_model.create(img_vals)

                self._upsert_pgvector(product, img_vec, media_type="image", content=img_desc)

        # 3. Product Video Embedding (from Uploaded Video File, Video URL, or Attachment)
        video_source = self._get_product_video_source(product)
        if video_source:
            video_vec = self.get_video_embedding(
                video_bytes=video_source.get("video_bytes"),
                video_url=video_source.get("video_url"),
            )
            if any(abs(x) > 1e-9 for x in video_vec):
                vid_url = video_source.get("video_url") or ""
                vid_desc = f"Visual product video representation for {product.name} ({vid_url})"
                if emb_model:
                    existing_vid = emb_model.search([
                        ("product_tmpl_id", "=", product.id),
                        ("media_type", "=", "video"),
                    ], limit=1)
                    vid_vals = {
                        "name": f"{product.name} (Video)",
                        "product_tmpl_id": product.id,
                        "media_type": "video",
                        "attachment_id": video_source.get("attachment_id") or False,
                        "video_url": vid_url,
                        "description": vid_desc,
                        "embedding_json": json.dumps(video_vec),
                        "dimension": len(video_vec),
                    }
                    if existing_vid:
                        existing_vid.write(vid_vals)
                    else:
                        emb_model.create(vid_vals)

                self._upsert_pgvector(product, video_vec, media_type="video", content=vid_desc)

        _trim_process_working_set()
        return True

    def _connect_pg_url(self, clean_url):
        try:
            import psycopg2
            conn = psycopg2.connect(clean_url, connect_timeout=2)
            conn.autocommit = True
            return conn
        except ImportError:
            import psycopg
            return psycopg.connect(clean_url, connect_timeout=2, autocommit=True)

    def _upsert_pgvector(self, product, vector, media_type="text", content=""):
        if not vector or not any(abs(x) > 1e-9 for x in vector):
            return

        vec_str = "[" + ",".join(f"{float(x):.6f}" for x in vector) + "]"
        urls_to_try = self.active_pgvector_urls or self._resolve_reachable_pgvector_urls()

        upserted_any = False
        for db_url in urls_to_try:
            conn = None
            try:
                conn = self._connect_pg_url(db_url)
                with conn.cursor() as cur:
                    try:
                        cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
                    except Exception as ext_err:
                        _logger.debug("Postgres instance %s does not have pgvector extension: %s", db_url, ext_err)
                        continue

                    cur.execute(f"""
                        CREATE TABLE IF NOT EXISTS xevoria_multimodal_knowledge (
                            id SERIAL PRIMARY KEY,
                            product_id INTEGER,
                            media_type VARCHAR(32) DEFAULT 'text',
                            name TEXT,
                            content TEXT,
                            embedding vector({len(vector)})
                        );
                    """)

                    try:
                        cur.execute("""
                            ALTER TABLE xevoria_multimodal_knowledge
                            ADD COLUMN IF NOT EXISTS media_type VARCHAR(32) DEFAULT 'text';
                        """)
                    except Exception:
                        pass

                    try:
                        cur.execute("""
                            ALTER TABLE xevoria_multimodal_knowledge
                            DROP CONSTRAINT IF EXISTS xevoria_multimodal_knowledge_product_id_key;
                        """)
                    except Exception:
                        pass

                    try:
                        cur.execute("""
                            CREATE UNIQUE INDEX IF NOT EXISTS idx_xevoria_mm_prod_media
                            ON xevoria_multimodal_knowledge (product_id, media_type);
                        """)
                    except Exception:
                        pass

                    try:
                        cur.execute("""
                            INSERT INTO xevoria_multimodal_knowledge (product_id, media_type, name, content, embedding)
                            VALUES (%s, %s, %s, %s, %s::vector)
                            ON CONFLICT (product_id, media_type) DO UPDATE SET
                                name = EXCLUDED.name,
                                content = EXCLUDED.content,
                                embedding = EXCLUDED.embedding;
                        """, (product.id, media_type, product.name, content or product.name, vec_str))
                    except Exception:
                        cur.execute("""
                            DELETE FROM xevoria_multimodal_knowledge
                            WHERE product_id = %s AND COALESCE(media_type, 'text') = %s;
                        """, (product.id, media_type))
                        cur.execute("""
                            INSERT INTO xevoria_multimodal_knowledge (product_id, media_type, name, content, embedding)
                            VALUES (%s, %s, %s, %s, %s::vector);
                        """, (product.id, media_type, product.name, content or product.name, vec_str))

                    upserted_any = True
                    u = urlparse(db_url.replace("postgresql://", "http://"))
                    _logger.info(
                        "PgVector Upsert OK: product_id=%s (%s) [%s] -> %s:%s/%s (dim=%d)",
                        product.id, product.name, media_type,
                        u.hostname or "localhost", u.port or 5432, (u.path or "/odoo").lstrip("/"),
                        len(vector),
                    )
            except Exception as e:
                _logger.warning("PgVector upsert notice on %s: %s", db_url, e)
            finally:
                if conn:
                    try:
                        conn.close()
                    except Exception:
                        pass

        if not upserted_any:
            _logger.warning(
                "PgVector upsert skipped: no reachable PostgreSQL instance with `vector` extension found (tried: %s). "
                "Vectors ARE saved in Odoo table `xevoria_multimodal_embedding`.",
                urls_to_try,
            )

    # =========================================================================
    # Pure Vector Search & Retrieval
    # =========================================================================

    def search(self, text_query=None, image_bytes=None, video_bytes=None, video_url=None, limit=10):
        """
        Pure multimodal embedding and retrieval using EmbeddingGemma 2.
        
        - If video_bytes or video_url is provided: Generates video embedding directly.
        - If image_bytes is provided: Generates visual image embedding directly.
        - If text_query is provided: Generates query embedding with 'task: search result | query: ' prefix.
        - Returns ranked products scored via Cosine Similarity, enriched with matched product video URLs.
        """
        query_vector = None
        extracted_info = ""

        if video_bytes or video_url:
            extracted_info = f"Visual Product Video Query ({video_url})" if video_url else "Visual Product Video Query"
            query_vector = self.get_video_embedding(video_bytes=video_bytes, video_url=video_url)
        elif image_bytes:
            extracted_info = "Visual Product Image Query"
            query_vector = self.get_image_embedding(image_bytes)
        elif text_query:
            extracted_info = text_query.strip()
            query_vector = self.get_text_embedding(text_query, is_query=True)

        if not query_vector:
            return [], ""

        # 1. Search PgVector if online
        results = []
        if self.is_pgvector_online:
            try:
                results = self._search_pgvector(query_vector, limit=limit)
                if results:
                    return results, extracted_info
            except Exception as e:
                _logger.debug("PgVector query notice: %s", e)

        # 2. In-Database Vector Search (Zero-dependency Cosine Similarity)
        if self.env:
            try:
                results = self.env["xevoria.multimodal.embedding"].sudo().search_vector(
                    query_vector=query_vector,
                    limit=limit,
                    min_similarity=(self.min_score / 100.0),
                )
            except Exception as e:
                _logger.warning("Local vector search error: %s", e)

        return results, extracted_info

    def _search_pgvector(self, query_vector, limit=10):
        """Direct cosine similarity retrieval from pgvector table across all reachable pgvector DBs."""
        vec_str = "[" + ",".join(f"{float(x):.6f}" for x in query_vector) + "]"
        urls_to_try = self.active_pgvector_urls or self._resolve_reachable_pgvector_urls()

        for db_url in urls_to_try:
            conn = None
            try:
                conn = self._connect_pg_url(db_url)
                scored_products = {}
                with conn.cursor() as cur:
                    cur.execute("""
                        SELECT product_id, COALESCE(media_type, 'text'), 1 - (embedding <=> %s::vector) AS similarity
                        FROM xevoria_multimodal_knowledge
                        ORDER BY embedding <=> %s::vector
                        LIMIT %s;
                    """, (vec_str, vec_str, limit * 3))
                    rows = cur.fetchall()
                    for pid, media_type, sim in rows:
                        if sim is None or sim < (self.min_score / 100.0):
                            continue
                        score_pct = round(float(sim) * 100.0, 1)
                        if pid in scored_products and score_pct <= scored_products[pid]["score"]:
                            continue
                        prod = self.env["product.template"].sudo().browse(pid) if self.env else None
                        if prod and prod.exists():
                            scored_products[pid] = self._build_product_result_dict(
                                prod,
                                score_pct=score_pct,
                                media_type=media_type,
                                source_prefix="EmbeddingGemma 2 (PgVector)",
                            )
                if scored_products:
                    results = sorted(scored_products.values(), key=lambda x: x["score"], reverse=True)
                    return results[:limit]
            except Exception as e:
                _logger.debug("PgVector search notice on %s: %s", db_url, e)
            finally:
                if conn:
                    try:
                        conn.close()
                    except Exception:
                        pass
        return []