/** @odoo-module **/

import { Composer } from "@mail/core/common/composer";
import { patch } from "@web/core/utils/patch";
import { useState, onWillStart } from "@odoo/owl";
import { getDataURLFromFile } from "@web/core/utils/urls";
import { rpc } from "@web/core/network/rpc";

const MAX_FILES = 5;
const MAX_SIZE = 10 * 1024 * 1024;
const ALLOWED_TYPES = new Set([
    "image/jpeg", "image/png", "image/gif", "image/webp",
    "video/mp4", "video/webm", "video/quicktime",
]);

/**
 * EXTENSION of the same Composer component portal_rating patches for the
 * star-rating widget. Adds:
 *  - "post anonymously" checkbox
 *  - drag-and-drop + file-picker for review media with client-side preview
 *  - uploads files via multipart HTTP route before post, then passes
 *    attachment ids in postData.review_attachment_ids
 *  - (Phase 4) optional per-aspect star pickers (Comfort, Battery Life…),
 *    fetched from /website_sale/review/aspects and posted as
 *    postData.review_aspect_ratings
 */
patch(Composer.prototype, {
    setup() {
        super.setup(...arguments);
        this.wsreState = useState({
            isAnonymous: false,
            mediaPreviews: [],   // {localId, name, mimetype, is_image, is_video, previewUrl, file?}
            uploading: false,
            uploadError: null,
            aspects: [],         // [{id, name}] configured for this product
            aspectValues: {},    // {aspectId: 1..5}
        });
        this._wsreLocalId = 0;
        if (this.env.displayRating && !this.message) {
            onWillStart(async () => {
                await this._wsreLoadAspects();
            });
        }
    },

    /**
     * Best-effort: resolve the product.template id of the page the
     * composer lives on, so we know which aspects to ask about.
     */
    _wsreResolveTemplateId() {
        const el = document.querySelector(
            "[data-res-model='product.template'][data-res-id], [data-product-template-id], input[name='product_template_id']"
        );
        if (el) {
            const v = el.getAttribute?.("data-res-id")
                || el.getAttribute?.("data-product-template-id")
                || el.value;
            const n = parseInt(v, 10);
            if (n) return n;
        }
        const m = window.location.pathname.match(/-(\d+)\/?$/);
        if (m) return parseInt(m[1], 10);
        return null;
    },

    async _wsreLoadAspects() {
        const tmplId = this._wsreResolveTemplateId();
        if (!tmplId) return;
        try {
            const result = await rpc("/website_sale/review/aspects", {
                product_tmpl_id: tmplId,
            });
            if (result?.ok) {
                this.wsreState.aspects = result.aspects || [];
            }
        } catch (_) {
            // Non-fatal: the review can still be posted without aspects.
        }
    },

    onWsreSetAspectValue(aspectId, value) {
        this.wsreState.aspectValues = {
            ...this.wsreState.aspectValues,
            [aspectId]: value,
        };
    },

    onToggleAnonymous(ev) {
        this.wsreState.isAnonymous = ev.target.checked;
    },

    // ---- Media pick / drop -------------------------------------------------


    /**
     * Best-effort: resolve the currently selected product.product id on a
     * website product page (combination picker). Returns null if unknown.
     */
    _wsreResolveProductId() {
        // 1) Explicit data attribute we may set on the page
        const root = document.querySelector("[data-product-id], [data-product_id], input[name='product_id']");
        if (root) {
            const v = root.getAttribute?.("data-product-id")
                || root.getAttribute?.("data-product_id")
                || root.value;
            const n = parseInt(v, 10);
            if (n) return n;
        }
        // 2) Odoo website_sale combination info (common in recent versions)
        const combo = document.querySelector(".js_product input[name='product_id'], #product_form input[name='product_id']");
        if (combo?.value) {
            const n = parseInt(combo.value, 10);
            if (n) return n;
        }
        // 3) URL query ?product_id=
        try {
            const u = new URL(window.location.href);
            const q = u.searchParams.get("product_id") || u.searchParams.get("variant_id");
            if (q) {
                const n = parseInt(q, 10);
                if (n) return n;
            }
        } catch (_) {}
        return null;
    },

    onWsreMediaClick() {
        const input = this.el?.querySelector?.(".o_wsre_media_input");
        if (input) {
            input.value = "";
            input.click();
        }
    },

    async onWsreMediaSelected(ev) {
        const files = Array.from(ev.target.files || []);
        await this._wsreAddFiles(files);
        ev.target.value = "";
    },

    onWsreDragOver(ev) {
        ev.preventDefault();
        ev.stopPropagation();
        ev.currentTarget.classList.add("o_wsre_dragover");
    },

    onWsreDragLeave(ev) {
        ev.preventDefault();
        ev.stopPropagation();
        ev.currentTarget.classList.remove("o_wsre_dragover");
    },

    async onWsreDrop(ev) {
        ev.preventDefault();
        ev.stopPropagation();
        ev.currentTarget.classList.remove("o_wsre_dragover");
        const files = Array.from(ev.dataTransfer?.files || []);
        await this._wsreAddFiles(files);
    },

    async _wsreAddFiles(files) {
        this.wsreState.uploadError = null;
        const remaining = MAX_FILES - this.wsreState.mediaPreviews.length;
        if (remaining <= 0) {
            this.wsreState.uploadError = `Maximum ${MAX_FILES} media files per review.`;
            return;
        }
        const accepted = [];
        for (const file of files.slice(0, remaining)) {
            const mimetype = (file.type || "").split(";")[0].trim().toLowerCase();
            if (!ALLOWED_TYPES.has(mimetype)) {
                this.wsreState.uploadError = `Unsupported type: ${file.name}`;
                continue;
            }
            if (file.size > MAX_SIZE) {
                this.wsreState.uploadError = `${file.name} exceeds 10 MiB limit.`;
                continue;
            }
            const localId = ++this._wsreLocalId;
            let previewUrl = "";
            if (mimetype.startsWith("image/")) {
                try {
                    previewUrl = await getDataURLFromFile(file);
                } catch {
                    previewUrl = "";
                }
            }
            accepted.push({
                localId,
                name: file.name,
                mimetype,
                is_image: mimetype.startsWith("image/"),
                is_video: mimetype.startsWith("video/"),
                previewUrl,
                file,
                attachmentId: null,
            });
        }
        this.wsreState.mediaPreviews = [...this.wsreState.mediaPreviews, ...accepted];
    },

    onWsreRemoveMedia(localId) {
        this.wsreState.mediaPreviews = this.wsreState.mediaPreviews.filter(
            (p) => p.localId !== localId
        );
        this.wsreState.uploadError = null;
    },

    async _wsreUploadPending() {
        const pending = this.wsreState.mediaPreviews.filter((p) => p.file && !p.attachmentId);
        if (!pending.length) {
            return this.wsreState.mediaPreviews
                .map((p) => p.attachmentId)
                .filter(Boolean);
        }
        this.wsreState.uploading = true;
        this.wsreState.uploadError = null;
        try {
            const formData = new FormData();
            for (const p of pending) {
                formData.append("ufile", p.file, p.name);
            }
            // CSRF token for type=http route
            const csrf = odoo?.csrf_token || document.querySelector('meta[name="csrf-token"]')?.content || "";
            if (csrf) {
                formData.append("csrf_token", csrf);
            }
            const response = await fetch("/website_sale/review/upload", {
                method: "POST",
                body: formData,
                credentials: "same-origin",
            });
            const data = await response.json();
            if (!data.ok) {
                this.wsreState.uploadError = data.error || "Upload failed.";
                return null;
            }
            // Map returned attachments back onto previews (order-preserving)
            const uploaded = data.attachments || [];
            let idx = 0;
            for (const p of this.wsreState.mediaPreviews) {
                if (p.file && !p.attachmentId && idx < uploaded.length) {
                    p.attachmentId = uploaded[idx].id;
                    p.url = uploaded[idx].url;
                    p.file = null; // free the File reference
                    idx++;
                }
            }
            return this.wsreState.mediaPreviews
                .map((p) => p.attachmentId)
                .filter(Boolean);
        } catch (e) {
            this.wsreState.uploadError = "Upload failed. Please try again.";
            return null;
        } finally {
            this.wsreState.uploading = false;
        }
    },

    get postData() {
        const postData = super.postData;
        if (this.env.displayRating && !this.message) {
            postData.is_review_anonymous = this.wsreState.isAnonymous;
            // Attachment ids are injected in the overridden send path below
            // via a temporary hold; keep postData clean for the getter.
            this.wsreState.isAnonymous = false;
        }
        return postData;
    },

    /**
     * Intercept send so we can upload media first, then pass attachment ids.
     * Falls back to super if this is not a new product-review composer.
     */
    async sendMessage() {
        if (!(this.env.displayRating && !this.message)) {
            return super.sendMessage(...arguments);
        }
        if (this.wsreState.uploading) {
            return;
        }
        const attachmentIds = await this._wsreUploadPending();
        if (attachmentIds === null) {
            // Upload error already set on state
            return;
        }
        // Temporarily patch postData to include attachment ids
        const originalPostData = Object.getOwnPropertyDescriptor(
            Object.getPrototypeOf(this),
            "postData"
        );
        // Simpler approach: stash on instance and read in a one-shot getter override
        this._wsrePendingAttachmentIds = attachmentIds;
        try {
            const result = await super.sendMessage(...arguments);
            this.wsreState.mediaPreviews = [];
            this.wsreState.aspectValues = {};
            return result;
        } finally {
            this._wsrePendingAttachmentIds = null;
        }
    },
});

// Ensure review_attachment_ids rides along in postData when present
const _origPostDataDesc = Object.getOwnPropertyDescriptor(Composer.prototype, "postData");
if (_origPostDataDesc && _origPostDataDesc.get) {
    // Already patched above; chain one more layer for attachment ids
    patch(Composer.prototype, {
        get postData() {
            const postData = super.postData;
            if (this._wsrePendingAttachmentIds?.length) {
                postData.review_attachment_ids = this._wsrePendingAttachmentIds;
            }
            // Variant attribution (Phase 2)
            const pid = this._wsreResolveProductId?.() || null;
            if (pid) {
                postData.review_product_id = pid;
            }
            // Aspect ratings (Phase 4) — only send aspects the shopper
            // actually rated (value > 0).
            const aspectValues = this.wsreState?.aspectValues || {};
            const rated = Object.entries(aspectValues).filter(([, v]) => v > 0);
            if (rated.length) {
                postData.review_aspect_ratings = Object.fromEntries(rated);
            }
            return postData;
        },
    });
}
