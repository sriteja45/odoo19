/** @odoo-module **/

/**
 * Backend 3D preview helper for product forms.
 * Finds containers with [data-product-3d-backend-preview] and initialises
 * an interactive model-viewer when a saved GLB/GLTF exists.
 *
 * Supports multi-model default via /website_product_3d/default_model/<id>
 * when data-prefer-default-model="1" is present.
 */
const MODEL_VIEWER_LOCAL = "/website_product_3d/static/lib/model-viewer.min.js";
// CDN fallback disabled by default – module must work offline after install.
const ALLOW_CDN_FALLBACK = false;
const MODEL_VIEWER_CDN = "https://ajax.googleapis.com/ajax/libs/model-viewer/3.5.0/model-viewer.min.js";
let modelViewerPromise;

function loadModelViewer() {
    if (window.customElements?.get("model-viewer")) {
        return Promise.resolve();
    }
    if (!modelViewerPromise) {
        modelViewerPromise = new Promise((resolve, reject) => {
            const tryLoad = (src, isFallback = false) => {
                if (document.querySelector(`script[src="${src}"]`)) {
                    const check = (attempts = 0) => {
                        if (window.customElements?.get("model-viewer")) resolve();
                        else if (attempts > 60) reject(new Error("model-viewer script present but not registered"));
                        else setTimeout(() => check(attempts + 1), 50);
                    };
                    check();
                    return;
                }
                const script = document.createElement("script");
                script.type = "module";
                script.src = src;
                script.onload = () => {
                    const wait = (attempts = 0) => {
                        if (window.customElements?.get("model-viewer")) resolve();
                        else if (attempts > 60) {
                            if (!isFallback && ALLOW_CDN_FALLBACK) tryLoad(MODEL_VIEWER_CDN, true);
                            else reject(new Error(
                                "model-viewer not registered. Ensure static/lib/model-viewer.min.js is present."
                            ));
                        } else setTimeout(() => wait(attempts + 1), 50);
                    };
                    wait();
                };
                script.onerror = () => {
                    if (!isFallback && ALLOW_CDN_FALLBACK) tryLoad(MODEL_VIEWER_CDN, true);
                    else reject(new Error(
                        "Failed to load local model-viewer. Module is designed to work without external CDN."
                    ));
                };
                document.head.appendChild(script);
            };
            tryLoad(MODEL_VIEWER_LOCAL);
        });
    }
    return modelViewerPromise;
}

/**
 * Try to extract the current record ID from the Odoo form.
 * Works with both legacy and modern form views.
 */
function getCurrentRecordId() {
    // Modern OWL form: look for data-res-id on the form or action manager
    const form = document.querySelector(".o_form_view");
    if (form) {
        // data-res-id is often present
        if (form.dataset.resId) return form.dataset.resId;
        // Fallback: look inside the form controller
        const resIdEl = form.querySelector("[data-res-id]");
        if (resIdEl?.dataset.resId) return resIdEl.dataset.resId;
    }
    // URL fallback: /web#id=123&model=product.template...
    const hash = window.location.hash || "";
    const match = hash.match(/[?&]id=(\d+)/);
    if (match) return match[1];
    return null;
}

/**
 * Check whether a multi-model list has at least one saved model.
 * Looks for rows in the One2many list that contain a .glb/.gltf filename.
 */
function hasMultiModel(container) {
    const page = container.closest(".o_notebook_content, .o_form_sheet, .o_form_view");
    if (!page) return false;
    // Look inside the product_3d_model_ids list
    const list = page.querySelector(".o_field_one2many[name='product_3d_model_ids'], .o_list_view");
    if (!list) return false;
    const text = list.textContent || "";
    return /\.(glb|gltf)/i.test(text);
}

/**
 * Check whether the legacy binary field currently has a value (saved).
 */
function hasSavedLegacyModel(container) {
    const fieldName = container.dataset.fieldName || "product_3d_model";
    const page = container.closest(".o_notebook_content, .o_form_sheet, .o_form_view");
    if (!page) return false;

    const filenameInput = page.querySelector(`input[name="${fieldName}_filename"], .o_field_binary input[type="text"]`);
    if (filenameInput && filenameInput.value && /\.(glb|gltf)$/i.test(filenameInput.value)) {
        return true;
    }

    const binaryWidget = page.querySelector(`.o_field_binary[name="${fieldName}"], .o_field_widget[name="${fieldName}"]`);
    if (binaryWidget) {
        const text = binaryWidget.textContent || "";
        if (/\.(glb|gltf)/i.test(text)) return true;
    }
    return false;
}

function hasAnyModel(container) {
    return hasMultiModel(container) || hasSavedLegacyModel(container);
}

function initBackendPreview(container) {
    if (!container || container.dataset.initialized === "1") return;

    const modelName = container.dataset.modelName || "product.template";
    const fieldName = container.dataset.fieldName || "product_3d_model";
    const preferDefault = container.dataset.preferDefaultModel === "1";
    const recordId = getCurrentRecordId();

    // Only initialise once we have a real saved record
    if (!recordId) {
        container.innerHTML = `<div class="text-muted small">Save the product first to see the 3D preview.</div>`;
        return;
    }

    // Build the URL: prefer the multi-model default endpoint when requested
    let expectedUrl;
    if (preferDefault && modelName === "product.template") {
        expectedUrl = `/website_product_3d/default_model/${recordId}`;
    } else {
        expectedUrl = `/website_product_3d/model/${modelName}/${recordId}/${fieldName}`;
    }

    // Avoid re-init if already showing the correct model
    if (container.dataset.currentUrl === expectedUrl && container.querySelector("model-viewer")) {
        return;
    }

    container.dataset.initialized = "1";
    container.dataset.currentUrl = expectedUrl;

    // Quick check: if we can detect no file, show message
    if (!hasAnyModel(container)) {
        container.innerHTML = `<div class="text-muted small">Upload and save a .glb / .gltf file (in the 3D Models list) to see the 3D preview.</div>`;
        // Allow re-check later
        container.dataset.initialized = "0";
        return;
    }

    container.innerHTML = `<div class="o_product_3d_backend_loading text-muted small">Loading 3D preview…</div>`;

    loadModelViewer()
        .then(() => {
            // Clear previous content
            container.innerHTML = "";

            const mv = document.createElement("model-viewer");
            mv.className = "o_product_3d_backend_preview_viewer";
            mv.setAttribute("camera-controls", "");
            mv.setAttribute("touch-action", "pan-y");
            mv.setAttribute("shadow-intensity", "1");
            mv.setAttribute("exposure", "1");
            mv.setAttribute("style", "width:100%;height:320px;max-width:520px;background:#f8f9fa;border:1px solid #dee2e6;border-radius:0.5rem;");
            mv.setAttribute("src", expectedUrl);

            const loading = document.createElement("div");
            loading.className = "o_product_3d_backend_loading text-muted small mt-1";
            loading.textContent = "Loading 3D preview…";

            mv.addEventListener("load", () => {
                loading.remove();
            }, { once: true });

            mv.addEventListener("error", () => {
                loading.textContent = "Could not load 3D model. Make sure a .glb / .gltf is uploaded in the 3D Models list (or legacy field) and the product is saved.";
                loading.classList.add("text-warning");
            }, { once: true });

            container.appendChild(mv);
            container.appendChild(loading);
        })
        .catch((err) => {
            container.innerHTML = `<div class="alert alert-warning mb-0 py-2">3D preview unavailable (${err.message})</div>`;
        });
}

function bootBackendPreviews() {
    document.querySelectorAll("[data-product-3d-backend-preview]").forEach((el) => {
        // Reset initialized flag when the form record changes
        const currentId = getCurrentRecordId();
        if (el.dataset.lastRecordId !== currentId) {
            el.dataset.initialized = "0";
            el.dataset.lastRecordId = currentId || "";
            el.dataset.currentUrl = "";
        }
        initBackendPreview(el);
    });
}

// Initial boot
if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", bootBackendPreviews, { once: true });
} else {
    bootBackendPreviews();
}

// Re-run after form re-renders / notebook tab switches.
//
// The backend re-renders constantly (every keystroke in a field can mutate the
// DOM), so an unfiltered observer on document.body re-ran this init several
// times per second. We only react when a preview container is actually added
// or removed.
const SELECTOR = "[data-product-3d-backend-preview]";

const observer = new MutationObserver((mutations) => {
    const relevant = mutations.some((mutation) =>
        [...mutation.addedNodes, ...mutation.removedNodes].some(
            (node) =>
                node.nodeType === 1 &&
                (node.matches?.(SELECTOR) || node.querySelector?.(SELECTOR))
        )
    );
    if (!relevant) return;
    clearTimeout(window.__product3dBackendReinit);
    window.__product3dBackendReinit = setTimeout(bootBackendPreviews, 400);
});

function startBackendObserver() {
    const scope = document.querySelector(".o_action_manager") || document.body;
    if (scope) {
        observer.observe(scope, { childList: true, subtree: true });
    }
}

if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", startBackendObserver, { once: true });
} else {
    startBackendObserver();
}
