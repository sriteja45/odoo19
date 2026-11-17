/** @odoo-module **/

// model-viewer is an ES module. Odoo's loadJS cannot load it (it contains `export`).
// We inject a real <script type="module"> tag that points at the *local* copy
// shipped with the module. The module is designed to work offline / without any
// external CDN after installation.
const MODEL_VIEWER_LOCAL = "/website_product_3d/static/lib/model-viewer.min.js";
// Optional soft fallback – disabled by default so the module never *requires*
// an external network request. Set to true only for debugging.
const ALLOW_CDN_FALLBACK = false;
const MODEL_VIEWER_CDN = "https://ajax.googleapis.com/ajax/libs/model-viewer/3.5.0/model-viewer.min.js";
let modelViewerPromise;

function loadModelViewer() {
    // Already registered → nothing to do
    if (window.customElements?.get("model-viewer")) {
        return Promise.resolve();
    }
    if (!modelViewerPromise) {
        modelViewerPromise = new Promise((resolve, reject) => {
            const tryLoad = (src, isFallback = false) => {
                // Script already in the DOM → just wait for the custom element
                if (document.querySelector(`script[src="${src}"]`)) {
                    const check = (attempts = 0) => {
                        if (window.customElements?.get("model-viewer")) {
                            resolve();
                        } else if (attempts > 60) {
                            reject(new Error("model-viewer script present but custom element never registered"));
                        } else {
                            setTimeout(() => check(attempts + 1), 50);
                        }
                    };
                    check();
                    return;
                }

                const script = document.createElement("script");
                script.type = "module";
                script.src = src;
                script.onload = () => {
                    const waitForElement = (attempts = 0) => {
                        if (window.customElements?.get("model-viewer")) {
                            resolve();
                        } else if (attempts > 60) {
                            if (!isFallback && ALLOW_CDN_FALLBACK) {
                                console.warn("[website_product_3d] Local model-viewer timed out, trying optional CDN");
                                tryLoad(MODEL_VIEWER_CDN, true);
                            } else {
                                reject(new Error(
                                    "model-viewer custom element was not registered. " +
                                    "Ensure static/lib/model-viewer.min.js is present and served correctly."
                                ));
                            }
                        } else {
                            setTimeout(() => waitForElement(attempts + 1), 50);
                        }
                    };
                    waitForElement();
                };
                script.onerror = () => {
                    if (!isFallback && ALLOW_CDN_FALLBACK) {
                        console.warn("[website_product_3d] Local model-viewer failed, trying optional CDN");
                        tryLoad(MODEL_VIEWER_CDN, true);
                    } else {
                        reject(new Error(
                            "Failed to load local model-viewer script. " +
                            "The module is designed to work without external CDN. " +
                            "Check that /website_product_3d/static/lib/model-viewer.min.js is reachable."
                        ));
                    }
                };
                document.head.appendChild(script);
            };

            tryLoad(MODEL_VIEWER_LOCAL);
        });
    }
    return modelViewerPromise;
}

function show3DError(wrapper, error) {
    console.warn("[website_product_3d] 3D model could not be loaded:", error || "unknown error");
    wrapper.classList.add("o_product_3d_error");
    wrapper.querySelector(".o_product_3d_error_message")?.classList.remove("d-none");
    wrapper.querySelector(".o_product_3d_loading")?.classList.add("d-none");
    wrapper.querySelector(".o_product_3d_progress")?.classList.add("d-none");
}

function setPanelState(container, type) {
    container.querySelectorAll(".o_product_3d_toggle").forEach((button) => {
        const active = button.dataset.viewerTarget === type;
        button.classList.toggle("active", active);
        button.setAttribute("aria-pressed", active ? "true" : "false");
    });
    container.querySelectorAll("[data-viewer-type]").forEach((panel) => {
        panel.classList.toggle("d-none", panel.dataset.viewerType !== type);
    });
}

function applyViewerOptions(wrapper, modelViewer) {
    if (wrapper.dataset.autoRotate === "1") {
        modelViewer.setAttribute("auto-rotate", "");
    } else {
        modelViewer.removeAttribute("auto-rotate");
    }
    if (wrapper.dataset.ar === "1") {
        modelViewer.setAttribute("ar", "");
    } else {
        modelViewer.removeAttribute("ar");
    }
    // Poster
    const posterUrl = wrapper.dataset.posterUrl;
    if (posterUrl) {
        modelViewer.setAttribute("poster", posterUrl);
    }
    // Camera controls
    const orbit = wrapper.dataset.cameraOrbit;
    if (orbit) {
        modelViewer.setAttribute("camera-orbit", orbit);
    }
    const fov = wrapper.dataset.fieldOfView;
    if (fov) {
        modelViewer.setAttribute("field-of-view", fov);
    } else {
        modelViewer.removeAttribute("field-of-view");
    }
}

function updateProgress(wrapper, percent) {
    const progressEl = wrapper.querySelector(".o_product_3d_progress");
    const bar = wrapper.querySelector(".o_product_3d_progress_bar");
    const text = wrapper.querySelector(".o_product_3d_progress_text");
    if (!progressEl) return;
    progressEl.classList.remove("d-none");
    if (bar) bar.style.width = `${Math.min(100, Math.max(0, percent))}%`;
    if (text) text.textContent = percent >= 100 ? "Almost ready…" : `Loading ${Math.round(percent)}%`;
}

function hideProgress(wrapper) {
    wrapper.querySelector(".o_product_3d_progress")?.classList.add("d-none");
}

function isUsdzUrl(url) {
    return typeof url === "string" && /\.usdz(\?|$)/i.test(url);
}

/**
 * Find a USDZ URL among the model switcher buttons (or data attributes)
 * so we can pair GLB (web 3D) with USDZ (iOS AR) when both exist.
 */
function findUsdzCompanion(wrapper, preferredUrl) {
    // Explicit data-ios-src on the wrapper wins
    if (wrapper.dataset.iosSrc) {
        return wrapper.dataset.iosSrc;
    }
    // Look through model switcher buttons for a .usdz entry
    const buttons = [...wrapper.querySelectorAll(".o_product_3d_model_btn")];
    for (const btn of buttons) {
        const u = btn.dataset.modelUrl || btn.dataset.downloadUrl || "";
        if (isUsdzUrl(u) && u !== preferredUrl) {
            return u;
        }
    }
    // If the preferred URL itself is USDZ, return it
    if (isUsdzUrl(preferredUrl)) {
        return preferredUrl;
    }
    return "";
}

/**
 * Load a 3D model into <model-viewer>.
 *
 * Architecture:
 *   GLB / GLTF  →  src          (desktop, Android, general web 3D)
 *   USDZ        →  ios-src      (iPhone / iPad AR via Quick Look)
 *
 * When both a GLB and a USDZ are available on the product, the GLB is
 * used for interactive viewing and the USDZ is attached as ios-src so
 * the AR button works natively on iOS.
 */
function load3DModel(wrapper, url) {
    const modelViewer = wrapper.querySelector("model-viewer");
    if (!modelViewer || !url) {
        return;
    }

    wrapper.classList.remove("o_product_3d_error", "o_product_3d_loaded");
    wrapper.querySelector(".o_product_3d_error_message")?.classList.add("d-none");
    wrapper.querySelector(".o_product_3d_loading")?.classList.remove("d-none");
    hideProgress(wrapper);
    applyViewerOptions(wrapper, modelViewer);

    // Update download link + suggested filename
    const downloadBtn = wrapper.querySelector(".o_product_3d_download");
    if (downloadBtn) {
        downloadBtn.href = url;
        const ext = isUsdzUrl(url) ? "usdz" : "glb";
        downloadBtn.setAttribute("download", `product-3d-model.${ext}`);
    }

    // Clean previous src / ios-src
    modelViewer.removeAttribute("src");
    modelViewer.removeAttribute("ios-src");

    const onProgress = (event) => {
        // model-viewer progress event: event.detail.totalProgress (0..1)
        const total = event.detail?.totalProgress;
        if (typeof total === "number") {
            updateProgress(wrapper, total * 100);
            if (total >= 1) {
                hideProgress(wrapper);
            }
        }
    };

    modelViewer.addEventListener("progress", onProgress);

    modelViewer.addEventListener("load", () => {
        wrapper.classList.add("o_product_3d_loaded");
        wrapper.querySelector(".o_product_3d_loading")?.classList.add("d-none");
        hideProgress(wrapper);
        modelViewer.removeEventListener("progress", onProgress);
    }, { once: true });

    modelViewer.addEventListener("error", (event) => {
        show3DError(wrapper, event);
        modelViewer.removeEventListener("progress", onProgress);
    }, { once: true });

    const usdzUrl = findUsdzCompanion(wrapper, url);

    if (isUsdzUrl(url)) {
        // Primary asset is USDZ → use it only for iOS AR.
        // Keep any previously successful non-USDZ src if present; otherwise
        // still set src so model-viewer has something to attempt on other platforms.
        modelViewer.setAttribute("ios-src", url);
        // Prefer a non-USDZ companion for the interactive web view if available
        const glbCompanion = [...wrapper.querySelectorAll(".o_product_3d_model_btn")]
            .map((b) => b.dataset.modelUrl || "")
            .find((u) => u && !isUsdzUrl(u));
        if (glbCompanion) {
            modelViewer.setAttribute("src", glbCompanion);
        } else {
            // USDZ-only product: still set src (model-viewer may show a poster /
            // limited preview on non-iOS). ios-src remains the AR source.
            modelViewer.setAttribute("src", url);
        }
    } else {
        // Primary asset is GLB/GLTF → interactive web view
        modelViewer.setAttribute("src", url);
        if (usdzUrl) {
            modelViewer.setAttribute("ios-src", usdzUrl);
        }
    }
}

function init3DViewer(wrapper) {
    if (!wrapper || wrapper.dataset.initialized === "1") {
        return;
    }
    wrapper.dataset.initialized = "1";

    // Store original template model URL so we can restore it when switching
    // away from a variant that has its own model.
    if (!wrapper.dataset.originalModelUrl) {
        wrapper.dataset.originalModelUrl = wrapper.dataset.modelUrl || "";
        wrapper.dataset.originalAutoRotate = wrapper.dataset.autoRotate || "1";
        wrapper.dataset.originalAr = wrapper.dataset.ar || "1";
        wrapper.dataset.originalCameraOrbit = wrapper.dataset.cameraOrbit || "0deg 75deg 105%";
        wrapper.dataset.originalFieldOfView = wrapper.dataset.fieldOfView || "";
    }

    // Defer the heavy model-viewer script until the panel is actually shown
    // or the root scrolls near the viewport (IntersectionObserver).
    // The first call to loadModelViewer() still happens when the user clicks
    // "3D View"; this only avoids downloading the library on pages where the
    // visitor never opens the 3D panel.

    // Model switcher buttons
    wrapper.querySelectorAll(".o_product_3d_model_btn").forEach((btn) => {
        btn.addEventListener("click", () => {
            // Update active button style
            wrapper.querySelectorAll(".o_product_3d_model_btn").forEach((b) => {
                b.classList.remove("btn-primary");
                b.classList.add("btn-outline-secondary");
            });
            btn.classList.remove("btn-outline-secondary");
            btn.classList.add("btn-primary");

            // Apply selected model options
            wrapper.dataset.modelUrl = btn.dataset.modelUrl || "";
            wrapper.dataset.autoRotate = btn.dataset.autoRotate || "1";
            wrapper.dataset.ar = btn.dataset.ar || "1";
            wrapper.dataset.cameraOrbit = btn.dataset.cameraOrbit || "0deg 75deg 105%";
            wrapper.dataset.fieldOfView = btn.dataset.fieldOfView || "";
            wrapper.dataset.downloadUrl = btn.dataset.downloadUrl || btn.dataset.modelUrl || "";

            load3DModel(wrapper, wrapper.dataset.modelUrl);
        });
    });

    // Reset Camera button
    const resetBtn = wrapper.querySelector(".o_product_3d_reset_camera");
    if (resetBtn && resetBtn.dataset.bound !== "1") {
        resetBtn.dataset.bound = "1";
        resetBtn.addEventListener("click", () => {
            const modelViewer = wrapper.querySelector("model-viewer");
            if (!modelViewer) return;
            const orbit = wrapper.dataset.cameraOrbit || "0deg 75deg 105%";
            const fov = wrapper.dataset.fieldOfView || "";
            // Restore configured orbit / FOV
            modelViewer.setAttribute("camera-orbit", orbit);
            if (fov) {
                modelViewer.setAttribute("field-of-view", fov);
            } else {
                modelViewer.removeAttribute("field-of-view");
            }
            // model-viewer helpers (supported in recent versions)
            try {
                if (typeof modelViewer.resetTurntableRotation === "function") {
                    modelViewer.resetTurntableRotation();
                }
                if (typeof modelViewer.jumpCameraToGoal === "function") {
                    modelViewer.jumpCameraToGoal();
                }
            } catch (e) {
                // ignore – attribute update is enough for most cases
            }
        });
    }

    loadModelViewer()
        .then(() => load3DModel(wrapper, wrapper.dataset.modelUrl))
        .catch((error) => show3DError(wrapper, error));
}

function initToolbar(container) {
    if (container.dataset.toolbarInitialized === "1") {
        return;
    }
    container.dataset.toolbarInitialized = "1";
    container.querySelectorAll(".o_product_3d_toggle").forEach((button) => {
        button.addEventListener("click", () => {
            const target = button.dataset.viewerTarget;
            const panel = container.querySelector(`[data-viewer-type="${target}"]`);
            const alreadyOpen = panel && !panel.classList.contains("d-none");
            if (alreadyOpen) {
                setPanelState(container, "__none__");
                return;
            }
            setPanelState(container, target);
            if (target === "3d") {
                init3DViewer(panel);
            } else if (target === "360") {
                init360Viewer(panel);
            } else if (target === "simple") {
                initSimpleAnimViewer(panel);
            }
        });
    });
}

/**
 * Lightweight CSS/JS rotate + zoom on a single product image.
 * No 3D model or multi-frame sequence required.
 */
function initSimpleAnimViewer(wrapper) {
    if (!wrapper || wrapper.dataset.initialized === "1") return;
    wrapper.dataset.initialized = "1";

    const stage = wrapper.querySelector(".o_product_simple_anim_stage");
    const inner = wrapper.querySelector(".o_product_simple_anim_inner");
    const img = wrapper.querySelector(".o_product_simple_anim_image");
    if (!stage || !inner || !img) return;

    let rotateY = 0;
    let scale = 1;
    let dragging = false;
    let startX = 0;
    let startRotate = 0;
    let moved = false;

    const apply = () => {
        inner.style.transform = `perspective(800px) rotateY(${rotateY}deg) scale(${scale})`;
    };

    const reset = () => {
        rotateY = 0;
        scale = 1;
        apply();
    };

    const onPointerDown = (event) => {
        if (event.button !== undefined && event.button !== 0) return;
        dragging = true;
        moved = false;
        startX = event.clientX;
        startRotate = rotateY;
        stage.setPointerCapture?.(event.pointerId);
        stage.classList.add("is-dragging");
    };

    const onPointerMove = (event) => {
        if (!dragging) return;
        const dx = event.clientX - startX;
        if (Math.abs(dx) > 2) moved = true;
        // ~0.4 deg per pixel feels natural
        rotateY = startRotate + dx * 0.4;
        apply();
        event.preventDefault();
    };

    const onPointerUp = (event) => {
        if (!dragging) return;
        dragging = false;
        stage.classList.remove("is-dragging");
        stage.releasePointerCapture?.(event.pointerId);
    };

    const onWheel = (event) => {
        event.preventDefault();
        const delta = event.deltaY > 0 ? -0.08 : 0.08;
        scale = Math.min(2.5, Math.max(0.6, scale + delta));
        apply();
    };

    // Pinch zoom (basic)
    let lastPinchDist = null;
    stage.addEventListener("touchstart", (event) => {
        if (event.touches.length === 2) {
            const dx = event.touches[0].clientX - event.touches[1].clientX;
            const dy = event.touches[0].clientY - event.touches[1].clientY;
            lastPinchDist = Math.hypot(dx, dy);
        }
    }, { passive: true });

    stage.addEventListener("touchmove", (event) => {
        if (event.touches.length === 2 && lastPinchDist !== null) {
            const dx = event.touches[0].clientX - event.touches[1].clientX;
            const dy = event.touches[0].clientY - event.touches[1].clientY;
            const dist = Math.hypot(dx, dy);
            const ratio = dist / lastPinchDist;
            scale = Math.min(2.5, Math.max(0.6, scale * ratio));
            lastPinchDist = dist;
            apply();
            event.preventDefault();
        }
    }, { passive: false });

    stage.addEventListener("touchend", () => {
        lastPinchDist = null;
    });

    stage.addEventListener("pointerdown", onPointerDown);
    stage.addEventListener("pointermove", onPointerMove, { passive: false });
    stage.addEventListener("pointerup", onPointerUp);
    stage.addEventListener("pointercancel", onPointerUp);
    stage.addEventListener("pointerleave", (event) => {
        if (dragging && event.pointerType === "mouse") onPointerUp(event);
    });
    stage.addEventListener("wheel", onWheel, { passive: false });
    stage.addEventListener("click", (event) => {
        if (moved) {
            event.preventDefault();
            event.stopPropagation();
        }
        moved = false;
    }, true);

    const resetBtn = wrapper.querySelector(".o_product_simple_anim_reset");
    if (resetBtn && resetBtn.dataset.bound !== "1") {
        resetBtn.dataset.bound = "1";
        resetBtn.addEventListener("click", reset);
    }

    apply();
}

function init360Viewer(wrapper) {
    if (!wrapper || wrapper.dataset.initialized === "1") return;
    wrapper.dataset.initialized = "1";
    const stage = wrapper.querySelector(".o_product_360_viewer_stage");
    const image = wrapper.querySelector(".o_product_360_image");
    // Supports both dedicated product.360.frame images and fallback product images.
    // Frames may use data-src (lazy) or src. Prefer data-src when present.
    const frameNodes = [...wrapper.querySelectorAll(".o_product_360_frames img")];
    if (!stage || !image || frameNodes.length < 2) return;

    const uniqueFrames = [];
    const seen = new Set();
    frameNodes.forEach((node) => {
        const src = node.getAttribute("data-src") || node.currentSrc || node.src || node.getAttribute("src");
        if (src && !seen.has(src)) {
            seen.add(src);
            uniqueFrames.push(src);
        }
    });
    if (uniqueFrames.length < 2) {
        wrapper.classList.add("d-none");
        const root = wrapper.closest(".o_product_3d_root");
        const btn = root?.querySelector('.o_product_3d_toggle[data-viewer-target="360"]');
        if (btn) btn.classList.add("d-none");
        return;
    }

    const sensitivity = Math.max(1, Number.parseFloat(wrapper.dataset.sensitivity || "6"));
    // How many neighbours on each side to keep preloaded
    const PRELOAD_RADIUS = 2;
    let currentFrame = 0;
    let startX = 0;
    let startFrame = 0;
    let dragging = false;
    let moved = false;
    const loading = wrapper.querySelector(".o_product_360_loading");
    const cache = new Map(); // src → Image (or true once loaded)

    const ensureLoaded = (index) => {
        const i = (index + uniqueFrames.length) % uniqueFrames.length;
        const src = uniqueFrames[i];
        if (cache.has(src)) return cache.get(src);
        const img = new Image();
        const promise = new Promise((resolve) => {
            img.onload = img.onerror = () => resolve(src);
        });
        img.src = src;
        cache.set(src, promise);
        return promise;
    };

    const preloadAround = (center) => {
        const jobs = [];
        for (let d = -PRELOAD_RADIUS; d <= PRELOAD_RADIUS; d++) {
            jobs.push(ensureLoaded(center + d));
        }
        return Promise.all(jobs);
    };

    loading?.classList.remove("opacity-0");

    // First paint: load current frame + neighbours, then hide spinner
    preloadAround(0).then(() => {
        loading?.classList.add("opacity-0");
        image.src = uniqueFrames[0];
    });

    const renderFrame = (index) => {
        currentFrame = (index + uniqueFrames.length) % uniqueFrames.length;
        const src = uniqueFrames[currentFrame];
        // Show immediately if already cached; otherwise wait for load
        if (cache.has(src)) {
            image.src = src;
        } else {
            ensureLoaded(currentFrame).then(() => {
                if (currentFrame === (index + uniqueFrames.length) % uniqueFrames.length) {
                    image.src = src;
                }
            });
        }
        // Keep neighbours warm while the user is interacting
        preloadAround(currentFrame);
    };

    const onPointerDown = (event) => {
        dragging = true;
        moved = false;
        startX = event.clientX;
        startFrame = currentFrame;
        stage.setPointerCapture?.(event.pointerId);
        stage.classList.add("is-dragging");
    };
    const onPointerMove = (event) => {
        if (!dragging) return;
        if (Math.abs(event.clientX - startX) > 2) moved = true;
        renderFrame(startFrame - Math.trunc((event.clientX - startX) / sensitivity));
        event.preventDefault();
    };
    const onPointerUp = (event) => {
        if (!dragging) return;
        dragging = false;
        stage.classList.remove("is-dragging");
        stage.releasePointerCapture?.(event.pointerId);
    };
    stage.addEventListener("pointerdown", onPointerDown);
    stage.addEventListener("pointermove", onPointerMove, { passive: false });
    stage.addEventListener("pointerup", onPointerUp);
    stage.addEventListener("pointercancel", onPointerUp);
    stage.addEventListener("pointerleave", (event) => {
        if (dragging && event.pointerType === "mouse") onPointerUp(event);
    });
    stage.addEventListener("keydown", (event) => {
        if (event.key === "ArrowLeft") {
            renderFrame(currentFrame - 1);
            event.preventDefault();
        } else if (event.key === "ArrowRight") {
            renderFrame(currentFrame + 1);
            event.preventDefault();
        }
    });
    stage.addEventListener("click", (event) => {
        if (moved) {
            event.preventDefault();
            event.stopPropagation();
        }
        moved = false;
    }, true);

    // Initial display (may still be loading)
    image.src = uniqueFrames[0];
}

/**
 * Get the currently selected product variant ID from the standard
 * website_sale product form.
 */
function getVariantId() {
    // Most reliable: the hidden product_id input that Odoo updates
    const input = document.querySelector('.js_product input[name="product_id"], form.js_add_cart_variants input[name="product_id"], input[name="product_id"]');
    if (input && input.value) return input.value;
    // Fallback: data attribute sometimes present on the combination info
    const combo = document.querySelector("[data-product-id], .js_product");
    if (combo?.dataset?.productId) return combo.dataset.productId;
    return null;
}

/**
 * Update the 3D viewer when the customer changes variant.
 * - If the new variant has its own model → use it
 * - Otherwise restore the original template / default model
 */
function updateVariantModel(root) {
    const wrapper = root.querySelector('[data-viewer-type="3d"]');
    if (!wrapper) return;

    // Ensure we have the original template values stored
    if (!wrapper.dataset.originalModelUrl) {
        wrapper.dataset.originalModelUrl = wrapper.dataset.modelUrl || "";
        wrapper.dataset.originalAutoRotate = wrapper.dataset.autoRotate || "1";
        wrapper.dataset.originalAr = wrapper.dataset.ar || "1";
        wrapper.dataset.originalCameraOrbit = wrapper.dataset.cameraOrbit || "0deg 75deg 105%";
        wrapper.dataset.originalFieldOfView = wrapper.dataset.fieldOfView || "";
    }

    const variantId = getVariantId();
    const entry = variantId
        ? root.querySelector(`[data-product-3d-variant-models] [data-variant-id="${variantId}"]`)
        : null;

    let newUrl, autoRotate, ar, orbit, fov;

    if (entry && entry.dataset.modelUrl) {
        // Variant-specific model
        newUrl = entry.dataset.modelUrl;
        autoRotate = entry.dataset.autoRotate ?? "1";
        ar = entry.dataset.ar ?? "1";
        orbit = wrapper.dataset.originalCameraOrbit;
        fov = wrapper.dataset.originalFieldOfView;
    } else {
        // Fall back to template / default model
        newUrl = wrapper.dataset.originalModelUrl || "";
        autoRotate = wrapper.dataset.originalAutoRotate || "1";
        ar = wrapper.dataset.originalAr || "1";
        orbit = wrapper.dataset.originalCameraOrbit || "0deg 75deg 105%";
        fov = wrapper.dataset.originalFieldOfView || "";
    }

    // Only reload if the URL actually changed
    if (wrapper.dataset.modelUrl === newUrl) return;

    wrapper.dataset.modelUrl = newUrl;
    wrapper.dataset.autoRotate = autoRotate;
    wrapper.dataset.ar = ar;
    wrapper.dataset.cameraOrbit = orbit;
    wrapper.dataset.fieldOfView = fov;

    const modelViewer = wrapper.querySelector("model-viewer");
    if (modelViewer && window.customElements?.get("model-viewer") && newUrl) {
        // If the 3D panel is currently visible, reload immediately
        if (!wrapper.classList.contains("d-none")) {
            load3DModel(wrapper, newUrl);
        } else {
            // Just update the src so next open is correct
            modelViewer.setAttribute("src", newUrl);
        }
    }
}

/**
 * Hide 360° button early if there are fewer than 2 unique images.
 * Called during init so the button never appears for useless sequences.
 */
function check360UniqueFrames(root) {
    const panel = root.querySelector('[data-viewer-type="360"]');
    if (!panel) return;
    const frameNodes = [...panel.querySelectorAll(".o_product_360_frames img")];
    const unique = [...new Set(
        frameNodes.map((n) => n.getAttribute("data-src") || n.currentSrc || n.src).filter(Boolean)
    )];
    if (unique.length < 2) {
        panel.classList.add("d-none");
        const btn = root.querySelector('.o_product_3d_toggle[data-viewer-target="360"]');
        if (btn) btn.classList.add("d-none");
    }
}

function initProduct3D(root) {
    if (root.dataset.product3dInited === "1") {
        // Still re-check variant in case of partial DOM updates
        updateVariantModel(root);
        return;
    }
    root.dataset.product3dInited = "1";

    const toolbar = root.querySelector('[data-product-3d-toolbar="1"]');
    if (!toolbar) return;

    check360UniqueFrames(root);
    initToolbar(root);
    updateVariantModel(root);

    // Simplified variant → 3D model switching
    // -------------------------------------------------------
    // Odoo updates the hidden product_id input when the customer
    // picks a variant. We watch that value and, when it changes,
    // look up the matching model and update the viewer.
    //
    // Single reliable path:
    //   1. form "change" (covers most UI interactions)
    //   2. product_id value watcher (covers programmatic writes)
    // No permanent polling timers, no duplicate click handlers.
    const scheduleVariantUpdate = () => {
        window.setTimeout(() => updateVariantModel(root), 60);
    };

    const productForm = document.querySelector(".js_product, form.js_add_cart_variants, #product_details");
    if (productForm && productForm.dataset.product3dVariantListener !== "1") {
        productForm.dataset.product3dVariantListener = "1";
        productForm.addEventListener("change", scheduleVariantUpdate);
    }

    const productIdInput = document.querySelector(
        '.js_product input[name="product_id"], form.js_add_cart_variants input[name="product_id"], input[name="product_id"]'
    );
    if (productIdInput && productIdInput.dataset.product3dWatch !== "1") {
        productIdInput.dataset.product3dWatch = "1";
        let lastValue = productIdInput.value;

        const check = () => {
            if (productIdInput.value !== lastValue) {
                lastValue = productIdInput.value;
                updateVariantModel(root);
            }
        };

        productIdInput.addEventListener("change", check);
        productIdInput.addEventListener("input", check);

        // Attribute mutations (some Odoo paths set the attribute)
        new MutationObserver(check).observe(productIdInput, {
            attributes: true,
            attributeFilter: ["value"],
        });

        // Programmatic assignment: input.value = "…" does not fire events.
        // Patch the setter once so we are notified exactly when Odoo writes.
        try {
            const descriptor = Object.getOwnPropertyDescriptor(
                window.HTMLInputElement.prototype, "value"
            );
            if (descriptor?.set && descriptor?.get) {
                Object.defineProperty(productIdInput, "value", {
                    configurable: true,
                    get() {
                        return descriptor.get.call(this);
                    },
                    set(newValue) {
                        descriptor.set.call(this, newValue);
                        window.setTimeout(check, 0);
                    },
                });
            }
        } catch (_e) {
            // Patching failed – form change + MutationObserver still cover
            // the majority of cases. No permanent poll is started.
        }
    }
}

/**
 * Initialise a single product 3D root once it is near the viewport.
 * IntersectionObserver avoids loading model-viewer / starting 360 preloads
 * for product blocks the visitor never scrolls to.
 */
function observeAndInit(root) {
    if (root.dataset.product3dObserved === "1") {
        // Already observed / inited – only refresh variant model if needed
        if (root.dataset.product3dInited === "1") {
            updateVariantModel(root);
        }
        return;
    }
    root.dataset.product3dObserved = "1";

    const start = () => initProduct3D(root);

    if (!("IntersectionObserver" in window)) {
        start();
        return;
    }
    const observer = new IntersectionObserver(
        (entries) => {
            for (const entry of entries) {
                if (entry.isIntersecting || entry.intersectionRatio > 0) {
                    start();
                    observer.unobserve(root);
                    break;
                }
            }
        },
        { root: null, rootMargin: "200px 0px", threshold: 0.01 }
    );
    observer.observe(root);
}

/**
 * Find all product 3D roots on the page and initialise them (once each).
 * Safe to call multiple times – roots already marked as observed/inited
 * are skipped or only have their variant model refreshed.
 */
function boot() {
    document.querySelectorAll(".o_product_3d_root").forEach(observeAndInit);
}

// Initial boot
if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot, { once: true });
} else {
    boot();
}

// Re-init only when a *new* .o_product_3d_root appears in the product area
// (website editor, partial AJAX re-render). Scoped to the product region so
 // unrelated page mutations (cart, chat, etc.) do not trigger work.
(function watchProductArea() {
    const scope =
        document.querySelector("#product_detail, #product_detail_main, main") ||
        document.body;
    if (!scope || scope.dataset.product3dAreaWatch === "1") return;
    scope.dataset.product3dAreaWatch = "1";

    let timer = null;
    const observer = new MutationObserver((mutations) => {
        const hasNewRoot = mutations.some((m) =>
            [...m.addedNodes].some(
                (node) =>
                    node.nodeType === 1 &&
                    (node.classList?.contains("o_product_3d_root") ||
                        node.querySelector?.(".o_product_3d_root"))
            )
        );
        if (!hasNewRoot) return;
        clearTimeout(timer);
        timer = setTimeout(boot, 150);
    });
    observer.observe(scope, { childList: true, subtree: true });
})();
