// Xevoria Multimodal Product Search Client Script (EmbeddingGemma 2)

// Global State
let selectedMediaFile = null;

// -------------------------------------------------------------
// Window Global Handlers (Always available for inline events)
// -------------------------------------------------------------
window.xevoriaHandleImageInput = function (input) {
    if (input && input.files && input.files[0]) {
        window.xevoriaHandleImageFile(input.files[0]);
    }
};

window.xevoriaHandleImageFile = function (file) {
    if (!file) return;
    selectedMediaFile = file;

    const previewBox = document.getElementById("imagePreviewBox");
    const previewImg = document.getElementById("imagePreviewImg");
    const previewVideo = document.getElementById("videoPreviewEl");
    const dropzoneContent = document.querySelector("#imageDropzone .dropzone-content");
    const note = document.getElementById("searchContextNote");
    const searchBtn = document.getElementById("btnExecuteMultimodalSearch");

    const isVideo = (file.type && file.type.startsWith("video/")) || /\.(mp4|webm|mov|avi|mkv)$/i.test(file.name || "");

    const reader = new FileReader();
    reader.onload = function (e) {
        if (isVideo) {
            if (previewImg) previewImg.classList.add("d-none");
            if (previewVideo) {
                previewVideo.src = e.target.result;
                previewVideo.classList.remove("d-none");
            }
        } else {
            if (previewVideo) {
                previewVideo.pause();
                previewVideo.src = "";
                previewVideo.classList.add("d-none");
            }
            if (previewImg) {
                previewImg.src = e.target.result;
                previewImg.classList.remove("d-none");
            }
        }
        if (previewBox) previewBox.classList.remove("d-none");
        if (dropzoneContent) dropzoneContent.classList.add("d-none");
        if (note) {
            const label = isVideo ? "Video Ready" : "Image Ready";
            note.innerHTML = `<span class="badge bg-success me-1">${label}</span> <strong>"${file.name}"</strong> (${(file.size / 1024).toFixed(1)} KB)`;
        }
        if (searchBtn) {
            searchBtn.classList.remove("btn-primary");
            searchBtn.classList.add("btn-success");
            searchBtn.innerHTML = `<i class="fa fa-search me-1"></i> Search Catalog with ${isVideo ? 'Video' : 'Image'}`;
        }
    };
    reader.readAsDataURL(file);
};

window.xevoriaRemoveImage = function () {
    selectedMediaFile = null;
    const imageInput = document.getElementById("imageInput");
    if (imageInput) imageInput.value = "";

    const previewBox = document.getElementById("imagePreviewBox");
    const previewImg = document.getElementById("imagePreviewImg");
    const previewVideo = document.getElementById("videoPreviewEl");
    const dropzoneContent = document.querySelector("#imageDropzone .dropzone-content");
    const note = document.getElementById("searchContextNote");
    const searchBtn = document.getElementById("btnExecuteMultimodalSearch");

    if (previewVideo) {
        previewVideo.pause();
        previewVideo.src = "";
        previewVideo.classList.add("d-none");
    }
    if (previewImg) previewImg.src = "";
    if (previewBox) previewBox.classList.add("d-none");
    if (dropzoneContent) dropzoneContent.classList.remove("d-none");
    if (note) note.textContent = "Media removed. Select another product photo/video, paste a video URL, or enter a text query.";
    if (searchBtn) {
        searchBtn.classList.remove("btn-success");
        searchBtn.classList.add("btn-primary");
        searchBtn.innerHTML = '<i class="fa fa-search me-1"></i> Search Catalog';
    }
};

window.xevoriaExecuteSearch = async function () {
    const textInput = document.getElementById("xevoriaTextQueryInput");
    const videoUrlInput = document.getElementById("xevoriaVideoUrlInput");
    const textQuery = textInput ? textInput.value.trim() : "";
    const videoUrl = videoUrlInput ? videoUrlInput.value.trim() : "";

    if (!selectedMediaFile && !textQuery && !videoUrl) {
        alert("Please select a product photo/video, paste a video URL, or enter a text query first.");
        return;
    }

    const searchLoader = document.getElementById("searchLoader");
    const searchResultsContainer = document.getElementById("searchResultsContainer");
    const loaderText = document.getElementById("loaderText");
    const resultsRow = document.getElementById("resultsRow");

    if (searchLoader) searchLoader.classList.remove("d-none");
    if (searchResultsContainer) searchResultsContainer.classList.add("d-none");
    if (resultsRow) resultsRow.innerHTML = "";
    if (loaderText) loaderText.textContent = "Generating 768-d EmbeddingGemma 2 vector & retrieving catalog...";

    const formData = new FormData();
    if (selectedMediaFile) {
        const isVideo = (selectedMediaFile.type && selectedMediaFile.type.startsWith("video/")) || /\.(mp4|webm|mov|avi|mkv)$/i.test(selectedMediaFile.name || "");
        formData.append("file", selectedMediaFile, selectedMediaFile.name || (isVideo ? "query_video.mp4" : "query_image.jpg"));
        formData.append("media_type", isVideo ? "video" : "image");
    } else if (videoUrl) {
        formData.append("video_url", videoUrl);
        formData.append("media_type", "video");
    } else {
        formData.append("media_type", "text");
    }
    if (textQuery) {
        formData.append("text_query", textQuery);
    }

    try {
        const response = await fetch("/shop/multimodal/search", {
            method: "POST",
            body: formData,
        });

        const data = await response.json();
        if (searchLoader) searchLoader.classList.add("d-none");

        if (!data.success) {
            alert(data.error || "Failed to execute multimodal vector search.");
            return;
        }

        renderSearchResults(data);
    } catch (err) {
        console.error("Vector search failed:", err);
        if (searchLoader) searchLoader.classList.add("d-none");
        alert("Search request failed: " + err.message);
    }
};

function renderSearchResults(data) {
    const searchResultsContainer = document.getElementById("searchResultsContainer");
    const resultsCountBadge = document.getElementById("resultsCountBadge");
    const resultsRow = document.getElementById("resultsRow");
    const extractedQueryHint = document.getElementById("extractedQueryHint");

    if (searchResultsContainer) searchResultsContainer.classList.remove("d-none");
    if (resultsCountBadge) resultsCountBadge.textContent = data.total || 0;

    if (extractedQueryHint) {
        if (data.extracted_query) {
            extractedQueryHint.textContent = `Target: "${data.extracted_query.substring(0, 70)}"`;
        } else {
            extractedQueryHint.textContent = "";
        }
    }

    if (!resultsRow) return;

    if (!data.results || data.results.length === 0) {
        resultsRow.innerHTML = `
            <div class="col-12 text-center py-4">
                <i class="fa fa-search fa-3x text-muted mb-2"></i>
                <h6 class="fw-bold">No Matching Indexed Products Found</h6>
                <p class="text-muted small">Only products indexed in the vector store above the minimum confidence threshold are returned.</p>
            </div>
        `;
        return;
    }

    let html = "";
    data.results.forEach(item => {
        const scoreClass = item.score >= 80 ? "bg-success" : (item.score >= 60 ? "bg-primary" : "bg-warning text-dark");
        const modalityBadge = item.matched_label ? `<span class="badge bg-secondary position-absolute top-0 start-0 m-2" style="font-size: 0.65rem; z-index: 2;">${item.matched_label}</span>` : "";

        // Build playable Matched Product Video section whenever the matched product has a video
        let matchedVideoHtml = "";
        if (item.has_video && (item.video_embed_url || item.video_url)) {
            let playerElement = "";
            if (item.video_embed_url) {
                playerElement = `
                    <div class="ratio ratio-16x9 rounded overflow-hidden shadow-sm">
                        <iframe src="${item.video_embed_url}" title="${item.name} Video" allowfullscreen="allowfullscreen" style="border: 0;"></iframe>
                    </div>
                `;
            } else {
                playerElement = `
                    <video src="${item.video_url}" controls="controls" preload="metadata" class="w-100 rounded shadow-sm" style="max-height: 170px; background: #000;">
                        Your browser does not support HTML5 video.
                    </video>
                `;
            }
            matchedVideoHtml = `
                <div class="mt-2 pt-2 border-top">
                    <div class="d-flex justify-content-between align-items-center mb-1">
                        <span class="badge bg-info text-dark" style="font-size: 0.7rem;">
                            <i class="fa fa-video-camera me-1"></i> Matched Product Video
                        </span>
                        ${item.video_url ? `<a href="${item.video_url}" target="_blank" rel="noopener" class="small text-decoration-none" style="font-size: 0.72rem;"><i class="fa fa-external-link"></i> Open</a>` : ""}
                    </div>
                    ${playerElement}
                </div>
            `;
        }

        html += `
            <div class="col-md-6 col-lg-4">
                <div class="card h-100 xevoria-product-match-card border shadow-sm">
                    <div class="position-relative text-center p-3 bg-light rounded-top">
                        ${modalityBadge}
                        <span class="badge ${scoreClass} position-absolute top-0 end-0 m-2" style="z-index: 2;">
                            ${item.score}% Match
                        </span>
                        <img src="${item.image_url}" alt="${item.name}" class="img-fluid" style="height: 120px; object-fit: contain;">
                    </div>
                    <div class="card-body d-flex flex-column p-3">
                        <h6 class="card-title fw-bold text-truncate mb-1" title="${item.name}">
                            <a href="${item.product_url}" class="text-dark text-decoration-none">${item.name}</a>
                        </h6>
                        <p class="text-muted small text-truncate-2 mb-2" style="font-size: 0.8rem; line-height: 1.2;">
                            ${item.description || 'No description available.'}
                        </p>
                        ${matchedVideoHtml}
                        <div class="mt-auto pt-2 d-flex justify-content-between align-items-center">
                            <span class="fw-bold text-primary">${item.formatted_price}</span>
                            <a href="${item.product_url}" class="btn btn-sm btn-outline-primary px-3">
                                View Product
                            </a>
                        </div>
                    </div>
                </div>
            </div>
        `;
    });

    resultsRow.innerHTML = html;
}

// -------------------------------------------------------------
// Auto-Initializer & Event Delegator
// -------------------------------------------------------------
function initMultimodalSearch() {
    const modalEl = document.getElementById("xevoriaMultimodalModal");
    if (!modalEl) return false;

    const imageInput = document.getElementById("imageInput");
    if (imageInput) {
        imageInput.onchange = function (e) {
            if (e.target.files && e.target.files[0]) {
                window.xevoriaHandleImageFile(e.target.files[0]);
            }
        };
    }

    const textInput = document.getElementById("xevoriaTextQueryInput");
    if (textInput) {
        textInput.onkeydown = function (e) {
            if (e.key === "Enter") {
                e.preventDefault();
                window.xevoriaExecuteSearch();
            }
        };
    }

    const videoUrlInput = document.getElementById("xevoriaVideoUrlInput");
    if (videoUrlInput) {
        videoUrlInput.onkeydown = function (e) {
            if (e.key === "Enter") {
                e.preventDefault();
                window.xevoriaExecuteSearch();
            }
        };
    }

    const imageDropzone = document.getElementById("imageDropzone");
    if (imageDropzone) {
        ["dragenter", "dragover"].forEach(evt => {
            imageDropzone.addEventListener(evt, (e) => {
                e.preventDefault();
                imageDropzone.classList.add("dragover");
            }, false);
        });

        ["dragleave", "drop"].forEach(evt => {
            imageDropzone.addEventListener(evt, (e) => {
                e.preventDefault();
                imageDropzone.classList.remove("dragover");
            }, false);
        });

        imageDropzone.addEventListener("drop", (e) => {
            if (e.dataTransfer && e.dataTransfer.files && e.dataTransfer.files[0]) {
                window.xevoriaHandleImageFile(e.dataTransfer.files[0]);
            }
        });
    }

    return true;
}

if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initMultimodalSearch);
} else {
    initMultimodalSearch();
}

document.addEventListener("show.bs.modal", function (e) {
    if (e.target && e.target.id === "xevoriaMultimodalModal") {
        initMultimodalSearch();
    }
});
