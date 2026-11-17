# Xevoria Multimodal AI Product Search (EmbeddingGemma 2 + PgVector)

An enterprise-grade multimodal search module for **Odoo 19.0** powered by Google's **EmbeddingGemma 2** (`google/embeddinggemma-2`). It maps text specifications, product photos, and product videos (from uploaded files or URLs) natively into a unified **768-dimensional vector space**, enabling high-accuracy cross-modal visual retrieval with dual-storage across Odoo's database and a standalone Docker **PgVector** container.

---

## Architecture & Features

- **Unified Vector Space**: Uses `google/embeddinggemma-2` (440M parameter vision-language model) to project text, images, and video frames into the same 768-d embedding space.
- **Cross-Modal Retrieval**: Searching with a product photo matches products by image, text specs, or video clip.
- **Dual Storage**:
  - **Odoo Internal DB**: `xevoria.multimodal.embedding` (Zero-dependency Cosine Similarity search).
  - **Docker PgVector**: `xevoria_multimodal_knowledge` on `localhost:5532/odoo` (High-speed indexed vector search via `1 - (embedding <=> %s::vector)`).
- **Comprehensive Video Ingestion**:
  - **Direct Upload**: Upload `.mp4`, `.webm`, or `.mov` files directly on the product form.
  - **Direct URLs**: Ingest direct `.mp4`/`.webm` video streams.
  - **YouTube & Vimeo**: Automatically extracts storyboard keyframes from YouTube and Vimeo links for real visual video embedding.
- **Matched Product Video Playback**: Search results automatically render an inline HTML5 `<video controls>` player or YouTube `<iframe>` when a matched product has an associated video.
- **Optimized for CPU & Windows**: Native AVX2 `torch.float32` execution (~0.8s per image/frame), 70 soft tokens, and dynamic watchdog memory headroom (8–10 GB) preventing worker timeouts.

---

## Prerequisites & System Requirements

### 1. Hardware & Operating System
- **Operating System**: Windows 10/11, Ubuntu 20.04+, or macOS.
- **RAM**: Minimum 8 GB (16 GB recommended for running Odoo + PyTorch + Docker simultaneously).
- **CPU**: Multi-core processor with AVX2 instruction support.
- **GPU (Optional)**: NVIDIA GPU with CUDA support for accelerated batch indexing.

### 2. Software Requirements
- **Odoo**: Odoo 19.0 (Community or Enterprise).
- **Python**: Python 3.10, 3.11, or 3.12 (matching Odoo 19's virtual environment).
- **Docker**: Docker Desktop (Windows) or Docker Engine (Linux).

### 3. Python Dependencies in Odoo Virtual Environment
Activate your Odoo virtual environment (e.g., `C:\odoo@19.0\venv\Scripts\activate`) and install:

```powershell
pip install torch transformers accelerate pillow opencv-python psycopg2-binary
```

| Package | Purpose |
| :--- | :--- |
| `torch` | PyTorch runtime for running model tensor operations. |
| `transformers` (v4.45+) | Hugging Face model architecture for `google/embeddinggemma-2`. |
| `pillow` | Image loading, resizing, and RGB conversion. |
| `opencv-python` | Extracting uniform video keyframes from MP4/WebM/MOV files. |
| `psycopg2-binary` | Direct high-speed connection from Odoo to Docker PgVector container. |

### 4. Docker PgVector Container Setup
Run the official `pgvector` container mapped to port `5532` (to avoid conflicting with Odoo's primary PostgreSQL on port `5432`):

```powershell
# Run PgVector Docker container
docker run -d --name pgvector-odoo -e POSTGRES_USER=odoo -e POSTGRES_PASSWORD=odoo -e POSTGRES_DB=odoo -p 5532:5432 pgvector/pgvector:pg16

# Verify vector extension is enabled inside the container
docker exec -it pgvector-odoo psql -U odoo -d odoo -c "CREATE EXTENSION IF NOT EXISTS vector;"
```

### 5. Odoo Server Limits (`odoo.conf`)
Multimodal AI models load weights into memory and require execution time during initial model load and batch indexing. Add or verify the following in your `odoo.conf`:

```ini
[options]
limit_memory_soft = 8589934592   ; 8 GB
limit_memory_hard = 10737418240  ; 10 GB
limit_time_real = 7200           ; 2 hours for batch jobs
limit_time_cpu = 7200
```

*(Note: The module also includes an automatic runtime patch in `multimodal_service.py` that raises these watchdog limits automatically upon module import).*

---

## Step-by-Step Guide to Create & Index Embeddings

### Step 1: Install or Upgrade the Module
1. Place the `xevoria_multimodal_search` folder into your custom addons directory (e.g., `C:\tsss\odoo_mouser_electronics\custom-addons\xevoria_multimodal_search`).
2. Restart Odoo with `-u xevoria_multimodal_search` to apply database schema changes:
   ```powershell
   python C:\odoo@19.0\odoo-bin -c C:\odoo@19.0\odoo.conf -d odoo -u xevoria_multimodal_search
   ```

### Step 2: Verify System Configuration
1. In Odoo, go to **Settings → General Settings → Multimodal Vector Search**:
   - **Model ID**: `google/embeddinggemma-2`
   - **Embedding Dimension**: `768`
   - **PgVector Database URL**: `postgresql://odoo:odoo@localhost:5532/odoo`
   - **Inference Device**: `auto` (or `cpu` / `cuda`)
   - **Min Match Score**: `25.0`
2. Save settings.

### Step 3: Attach Media to Products
1. Navigate to **Website → eCommerce → Products** (or **Sales → Products**).
2. Open a product form (e.g., `TELVAS AM TAB`).
3. Set the product photo in the standard Odoo image field (`image_1920`).
4. In the **General Information** tab, locate the **EmbeddingGemma 2 Multimodal Video (URL or Upload)** section:
   - **Option A (By URL)**: Paste a direct video link (`.mp4`/`.webm`) or a YouTube/Vimeo URL in the **Product Video URL** field.
   - **Option B (By Upload)**: Click **Upload your file** next to **Upload Product Video** and select an `.mp4`, `.webm`, or `.mov` file from your computer.
5. Save the product record.

### Step 4: Generate Embeddings

#### Method A: Single Product Indexing
On the product form, click the **EmbeddingGemma Index** stat button in the top button box.
- The service extracts the product's text specifications, photo, and video frames.
- Generates 768-d vectors for each modality.
- Saves the embeddings into both Odoo and Docker PgVector.
- A green notification confirms successful indexing.

#### Method B: Batch Indexing via Action Menu
1. From the Products List view, select multiple products using the checkboxes.
2. Click **Action → Index with EmbeddingGemma 2**.
3. The server processes products sequentially, committing database progress after each product to ensure no data loss.

### Step 5: Verify Generated Vectors

#### In Docker PgVector:
Run this command in PowerShell to inspect the indexed vectors across modalities:
```powershell
docker exec -it pgvector-odoo psql -U odoo -d odoo -c "SELECT id, product_id, media_type, name, vector_dims(embedding) AS dims, LEFT(embedding::text, 50) AS vector_preview FROM xevoria_multimodal_knowledge ORDER BY id DESC;"
```

*Expected Output:*
```text
 id | product_id | media_type |     name      | dims |                   vector_preview
----+------------+------------+---------------+------+----------------------------------------------------
  3 |         35 | video      | TELVAS AM TAB |  768 | [-0.041201,0.012580,0.031924,-0.005120,-0.021840,0.
  2 |         35 | image      | TELVAS AM TAB |  768 | [-0.084007,0.005278,0.043962,0.008651,-0.030469,0.
  1 |         35 | text       | TELVAS AM TAB |  768 | [-0.033307,-0.013085,0.05262,-0.012595,-0.043943,0
(3 rows)
```

#### In Odoo Interface:
Navigate to **Website → Configuration → Multimodal Vectors** (`xevoria.multimodal.embedding`) to view stored records, full JSON embeddings, and modality breakdown badges.

---

## Testing Multimodal Search & Video Display

1. Open your Odoo eCommerce website at `http://localhost:8069/shop`.
2. Click the **Camera icon** in the search bar to launch the **Multimodal AI Product Search** modal.
3. Perform a search using any modality:
   - **Image Search**: Drag and drop a product image into the dropzone.
   - **Video Search**: Drop an MP4 clip or paste a video URL.
   - **Text / Spec Query**: Enter part numbers, brand names, or specifications.
4. Click **Search Catalog**.
5. **Results Display**:
   - Matching products appear ranked by Cosine Similarity percentage.
   - The matched modality badge (e.g., `EmbeddingGemma 2 (image)`) is shown.
   - If the matched product has an uploaded video or video URL, a **Matched Product Video** player appears directly inside the card with playback controls.

---

## Cleaning & Maintenance

### How to Clean / Reset Embeddings

#### 1. In Odoo Database:
- Go to **Website → Configuration → Multimodal Vectors**.
- Select all records and click **Action → Delete**.
- Or via Odoo developer shell:
  ```python
  env['xevoria.multimodal.embedding'].search([]).unlink()
  env['product.template'].search([]).write({'is_multimodal_indexed': False})
  env.cr.commit()
  ```

#### 2. In Docker PgVector Container:
To truncate all stored vectors in the PgVector container:
```powershell
docker exec -it pgvector-odoo psql -U odoo -d odoo -c "TRUNCATE TABLE xevoria_multimodal_knowledge RESTART IDENTITY;"
```

To delete vectors for a specific product ID (e.g., product 35):
```powershell
docker exec -it pgvector-odoo psql -U odoo -d odoo -c "DELETE FROM xevoria_multimodal_knowledge WHERE product_id = 35;"
```

---

## Troubleshooting Guide

| Issue | Root Cause | Solution |
| :--- | :--- | :--- |
| **`Virtual real time limit reached`** | CPU inference taking >600s with bfloat16 emulation or too many tokens. | Ensure `torch.float32` is used on CPU with `max_soft_tokens=70`. Verified in latest `multimodal_service.py`. |
| **`Server memory limit reached`** | Worker memory exceeding Windows 2 GB default. | Set `limit_memory_soft = 8589934592` in `odoo.conf` (automatically applied by module patch). |
| **Unindexed product showing high match** | Legacy filename SQL `ilike` fallback. | Upgrade to the latest version of `controllers/main.py` where fake fallbacks have been eliminated. |
| **Video doesn't play in card** | Video format unsupported by browser or missing route. | Upload `.mp4` (H.264) or `.webm` files; streaming endpoint `/shop/multimodal/product_video/<id>` handles byte streaming. |
