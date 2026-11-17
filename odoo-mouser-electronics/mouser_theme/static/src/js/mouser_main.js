/** @odoo-module **/

(function () {
    "use strict";

    const slides = [
        {
            cls: "hero-slide-roadshow",
            html: `<h1>Join Mouser at<br/>Technical Roadshow</h1><p><i class="fa fa-calendar"></i> June 12 - July 3</p><p><i class="fa fa-map-marker"></i> Pune | Bengaluru | Chennai</p>`,
        },
        {
            cls: "hero-slide-source",
            html: `<h1>Trust the source.<br/>Choose Mouser.</h1><p>The building blocks for engineers start here</p>`,
        },
        {
            cls: "hero-slide-amphenol",
            html: `<h1>Broadest portfolio of<br/>Amphenol products</h1><p>Connectors, sensors, antennas and more</p>`,
        },
        {
            cls: "hero-slide-newest",
            html: `<h1>The Newest Products for<br/>Your Newest Designs®</h1><p>Explore the latest electronic components</p>`,
        },
    ];

    function initHeroSlider() {
        const hero = document.querySelector(".mouser-homepage .hero-roadshow");
        if (!hero || hero.dataset.sliderReady === "1") {
            return;
        }
        hero.dataset.sliderReady = "1";

        const copy = hero.querySelector(".hero-copy");
        const dotsBox = hero.querySelector(".hero-dots");
        if (!copy || !dotsBox) {
            return;
        }

        let current = 0;
        let paused = false;
        let timer = null;

        dotsBox.innerHTML = `<button type="button" class="hero-pause" aria-label="Pause slider"><i class="fa fa-pause"></i></button>` +
            slides.map((s, i) => `<button type="button" class="hero-dot ${i === 0 ? "active" : ""}" data-index="${i}" aria-label="Go to slide ${i + 1}"></button>`).join("");

        const pauseButton = dotsBox.querySelector(".hero-pause");
        const dotButtons = dotsBox.querySelectorAll(".hero-dot");

        function showSlide(index) {
            current = (index + slides.length) % slides.length;

            slides.forEach((slide) => hero.classList.remove(slide.cls));
            hero.classList.add(slides[current].cls);
            copy.innerHTML = slides[current].html;

            dotButtons.forEach((dot, i) => {
                dot.classList.toggle("active", i === current);
            });
        }

        function start() {
            stop();
            timer = window.setInterval(function () {
                if (!paused) {
                    showSlide(current + 1);
                }
            }, 3500);
        }

        function stop() {
            if (timer) {
                window.clearInterval(timer);
                timer = null;
            }
        }

        dotButtons.forEach((dot) => {
            dot.addEventListener("click", function () {
                showSlide(parseInt(this.dataset.index, 10));
                start();
            });
        });

        pauseButton.addEventListener("click", function () {
            paused = !paused;
            this.innerHTML = paused ? '<i class="fa fa-play"></i>' : '<i class="fa fa-pause"></i>';
        });

        showSlide(0);
        start();
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", initHeroSlider);
    } else {
        initHeroSlider();
    }

    // Odoo may replace frontend DOM after normal DOMContentLoaded in some cases.
    window.setTimeout(initHeroSlider, 500);
    window.setTimeout(initHeroSlider, 1500);
})();

(function () {
    "use strict";

    function initPriceAvailabilityPage() {
        const page = document.querySelector(".price-availability-page");
        if (!page || page.dataset.paReady === "1") {
            return;
        }
        page.dataset.paReady = "1";

        page.querySelectorAll(".pa-panel-header").forEach((header) => {
            header.addEventListener("click", function () {
                const panel = this.closest(".pa-panel");
                panel.classList.toggle("is-open");
                const icon = this.querySelector("i");
                if (icon) {
                    icon.classList.toggle("fa-chevron-up", panel.classList.contains("is-open"));
                    icon.classList.toggle("fa-chevron-down", !panel.classList.contains("is-open"));
                }
            });
        });

        const rows = page.querySelector("#paManualRows");
        const addButton = page.querySelector("#paAddRows");
        const addCount = page.querySelector("#paAddCount");
        if (rows && addButton && addCount) {
            addButton.addEventListener("click", function () {
                const count = Math.max(1, Math.min(50, parseInt(addCount.value || "1", 10)));
                const start = rows.querySelectorAll("tr").length + 1;
                for (let i = 0; i < count; i++) {
                    const line = start + i;
                    const tr = document.createElement("tr");
                    tr.innerHTML = `<td>${line}</td><td><input type="text"></td><td><input type="text"></td><td><input type="number" value="1" min="1"></td><td><input type="number" min="1"></td><td><input type="number" min="1"></td>`;
                    rows.appendChild(tr);
                }
            });
        }

        const result = page.querySelector("#paResult");
        page.querySelectorAll(".pa-check-btn").forEach((button) => {
            button.addEventListener("click", function () {
                if (result) {
                    result.classList.remove("d-none");
                    result.scrollIntoView({behavior: "smooth", block: "center"});
                }
            });
        });

        const dropzone = page.querySelector("#paDropzone");
        const fileInput = page.querySelector("#paFileInput");
        const fileName = page.querySelector("#paFileName");
        function showFile(file) {
            if (fileName && file) {
                fileName.textContent = "Selected file: " + file.name;
            }
        }
        if (dropzone && fileInput) {
            ["dragenter", "dragover"].forEach((eventName) => {
                dropzone.addEventListener(eventName, function (ev) {
                    ev.preventDefault();
                    dropzone.classList.add("drag-over");
                });
            });
            ["dragleave", "drop"].forEach((eventName) => {
                dropzone.addEventListener(eventName, function (ev) {
                    ev.preventDefault();
                    dropzone.classList.remove("drag-over");
                });
            });
            dropzone.addEventListener("drop", function (ev) {
                const file = ev.dataTransfer && ev.dataTransfer.files && ev.dataTransfer.files[0];
                showFile(file);
            });
            fileInput.addEventListener("change", function () {
                showFile(this.files && this.files[0]);
            });
        }
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", initPriceAvailabilityPage);
    } else {
        initPriceAvailabilityPage();
    }
    window.setTimeout(initPriceAvailabilityPage, 500);
})();

(function () {
    "use strict";

    function initProjectBasketSharing() {
        const page = document.querySelector(".project-share-page");
        if (!page || page.dataset.pbsReady === "1") {
            return;
        }
        page.dataset.pbsReady = "1";
        const button = page.querySelector("#pbsSubmit");
        const input = page.querySelector(".pbs-access-row input");
        const message = page.querySelector("#pbsMessage");
        if (button && input && message) {
            button.addEventListener("click", function () {
                message.classList.remove("d-none");
                if (input.value.trim()) {
                    message.textContent = "Access ID received. Connect this demo to your Odoo project/basket sharing logic next.";
                } else {
                    message.textContent = "Please enter a valid Access ID. This demo form can be connected to Odoo project/basket records.";
                }
            });
        }
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", initProjectBasketSharing);
    } else {
        initProjectBasketSharing();
    }
    window.setTimeout(initProjectBasketSharing, 500);
})();


(function () {
    "use strict";

    function initQuoteRequestPage() {
        const page = document.querySelector(".quote-request-page");
        if (!page || page.dataset.qrfReady === "1") {
            return;
        }
        page.dataset.qrfReady = "1";

        const rows = page.querySelector("#qrfRows");
        const addButton = page.querySelector("#qrfAddLines");
        const addCount = page.querySelector("#qrfAddCount");

        function renumberRows() {
            if (!rows) return;
            rows.querySelectorAll("tr").forEach((tr, index) => {
                const firstCell = tr.querySelector("td");
                if (firstCell) firstCell.textContent = index + 1;
            });
        }

        function attachRemove(button) {
            button.addEventListener("click", function () {
                const allRows = rows.querySelectorAll("tr");
                if (allRows.length > 1) {
                    this.closest("tr").remove();
                    renumberRows();
                }
            });
        }

        if (rows) {
            rows.querySelectorAll(".qrf-remove").forEach(attachRemove);
        }

        if (rows && addButton && addCount) {
            addButton.addEventListener("click", function () {
                const count = Math.max(1, Math.min(50, parseInt(addCount.value || "1", 10)));
                const start = rows.querySelectorAll("tr").length + 1;
                for (let i = 0; i < count; i++) {
                    const tr = document.createElement("tr");
                    tr.innerHTML = `<td>${start + i}</td><td><input type="text"></td><td><input type="number" min="1"></td><td><button type="button" class="qrf-remove"><i class="fa fa-trash"></i></button></td>`;
                    rows.appendChild(tr);
                    attachRemove(tr.querySelector(".qrf-remove"));
                }
            });
        }

        const send = page.querySelector("#qrfSendRequest");
        const message = page.querySelector("#qrfMessage");
        if (send && message) {
            send.addEventListener("click", function () {
                message.classList.remove("d-none");
                message.scrollIntoView({behavior: "smooth", block: "center"});
            });
        }
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", initQuoteRequestPage);
    } else {
        initQuoteRequestPage();
    }
    window.setTimeout(initQuoteRequestPage, 500);
})();

(function () {
    "use strict";

    function initConversionCalculators() {
        const page = document.querySelector(".conversion-page");
        if (!page || page.dataset.conversionReady === "1") {
            return;
        }
        page.dataset.conversionReady = "1";

        page.querySelectorAll("[data-calc-target]").forEach((button) => {
            button.addEventListener("click", function () {
                const target = page.querySelector("#" + this.dataset.calcTarget);
                if (!target) return;
                page.querySelectorAll(".calculator-panel").forEach((panel) => panel.classList.remove("active"));
                target.classList.add("active");
                target.scrollIntoView({behavior: "smooth", block: "center"});
            });
        });

        const resistorButton = page.querySelector("#calc-resistor-btn");
        const resistorResult = page.querySelector("#resistor-result");
        const formatOhms = (value) => {
            if (value >= 1000000) return (value / 1000000).toFixed(2).replace(/\.00$/, "") + " MΩ";
            if (value >= 1000) return (value / 1000).toFixed(2).replace(/\.00$/, "") + " kΩ";
            return value.toFixed(2).replace(/\.00$/, "") + " Ω";
        };
        if (resistorButton && resistorResult) {
            resistorButton.addEventListener("click", function () {
                const b1 = parseInt(page.querySelector("#band1")?.value || "0", 10);
                const b2 = parseInt(page.querySelector("#band2")?.value || "0", 10);
                const mult = parseFloat(page.querySelector("#multiplier")?.value || "1");
                const tol = page.querySelector("#tolerance")?.value || "±5%";
                const resistance = ((b1 * 10) + b2) * mult;
                resistorResult.textContent = "Result: " + formatOhms(resistance) + " " + tol;
            });
        }

        const ohmsButton = page.querySelector("#calc-ohms-btn");
        const ohmsResult = page.querySelector("#ohms-result");
        const clearButton = page.querySelector("#clear-ohms-btn");
        if (ohmsButton && ohmsResult) {
            ohmsButton.addEventListener("click", function () {
                const vInput = page.querySelector("#ohm-v");
                const iInput = page.querySelector("#ohm-i");
                const rInput = page.querySelector("#ohm-r");
                const pInput = page.querySelector("#ohm-p");
                let v = parseFloat(vInput.value);
                let i = parseFloat(iInput.value);
                let r = parseFloat(rInput.value);

                if (!isNaN(v) && !isNaN(i)) {
                    r = v / i;
                } else if (!isNaN(v) && !isNaN(r)) {
                    i = v / r;
                } else if (!isNaN(i) && !isNaN(r)) {
                    v = i * r;
                } else {
                    ohmsResult.textContent = "Please enter any two values.";
                    return;
                }

                const p = v * i;
                vInput.value = Number.isFinite(v) ? v.toFixed(3).replace(/\.000$/, "") : "";
                iInput.value = Number.isFinite(i) ? i.toFixed(3).replace(/\.000$/, "") : "";
                rInput.value = Number.isFinite(r) ? r.toFixed(3).replace(/\.000$/, "") : "";
                pInput.value = Number.isFinite(p) ? p.toFixed(3).replace(/\.000$/, "") : "";
                ohmsResult.textContent = `Result: V=${vInput.value} V, I=${iInput.value} A, R=${rInput.value} Ω, P=${pInput.value} W`;
            });
        }
        if (clearButton) {
            clearButton.addEventListener("click", function () {
                ["#ohm-v", "#ohm-i", "#ohm-r", "#ohm-p"].forEach((selector) => {
                    const input = page.querySelector(selector);
                    if (input) input.value = "";
                });
                if (ohmsResult) ohmsResult.textContent = "Enter voltage/current, voltage/resistance, or current/resistance.";
            });
        }
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", initConversionCalculators);
    } else {
        initConversionCalculators();
    }
    window.setTimeout(initConversionCalculators, 500);
})();

/* Disabled duplicate old homepage slider. Final Mouser carousel below controls the banner. */


/* Final guard: remove duplicate product-name links in Newest Products cards.
   Some old Odoo/QWeb cached templates may still render two anchors. Keep only one. */
(function () {
    function fixNewestProductDuplicateNames() {
        document.querySelectorAll('.mouser-homepage .newest-section .new-card, .mouser-homepage .newest-section .original-product-card').forEach(function (card) {
            var links = Array.from(card.querySelectorAll('a'));
            if (!links.length) return;

            // Prefer the first visible product link, because original Mouser shows one small link below the image.
            var keep = links[0];
            links.slice(1).forEach(function (link) {
                link.remove();
            });
            keep.classList.add('mouser-single-product-name');
            keep.style.fontSize = '14px';
            keep.style.lineHeight = '1.25';
            keep.style.fontWeight = '400';
            keep.style.textAlign = 'center';
            keep.style.display = 'block';
            keep.style.margin = '8px auto 0';
            keep.style.padding = '0 12px 10px';
            keep.style.color = '#006dcc';
            keep.style.textDecorationLine = 'underline';
            keep.style.textDecorationStyle = 'dotted';
            keep.style.textUnderlineOffset = '3px';
        });
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', fixNewestProductDuplicateNames);
    } else {
        fixNewestProductDuplicateNames();
    }
    window.setTimeout(fixNewestProductDuplicateNames, 300);
    window.setTimeout(fixNewestProductDuplicateNames, 1000);
})();


/* 2026-05-03 final guard: newest product name only once */
(function () {
    function finalNewestProductsOneName() {
        document.querySelectorAll('.mouser-homepage .newest-section .original-product-card').forEach(function (card) {
            card.querySelectorAll('.original-product-img-wrap a').forEach(function (a) { a.remove(); });
            var links = Array.from(card.querySelectorAll('a'));
            if (!links.length) return;
            var keep = links.find(function(a){ return a.classList.contains('mouser-only-product-name'); }) || links[links.length - 1];
            links.forEach(function (a) { if (a !== keep) a.remove(); });
            keep.className = 'new-product-name mouser-only-product-name';
            keep.style.display = 'block';
            keep.style.width = '100%';
            keep.style.maxWidth = '180px';
            keep.style.margin = '5px auto 0';
            keep.style.padding = '0 8px 8px';
            keep.style.fontSize = '14px';
            keep.style.lineHeight = '1.22';
            keep.style.fontWeight = '400';
            keep.style.textAlign = 'center';
            keep.style.color = '#006dcc';
            keep.style.textDecorationLine = 'underline';
            keep.style.textDecorationStyle = 'dotted';
            keep.style.textUnderlineOffset = '3px';
        });
    }
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', finalNewestProductsOneName);
    } else {
        finalNewestProductsOneName();
    }
    window.setTimeout(finalNewestProductsOneName, 300);
    window.setTimeout(finalNewestProductsOneName, 1000);
})();


/* REAL FINAL FIX: ensure exactly one Newest Product title exists and it is visible. */
(function () {
    function enforceOneNewestProductName() {
        document.querySelectorAll('.mouser-homepage .newest-section .original-product-card').forEach(function (card) {
            var img = card.querySelector('.original-product-img');
            var title = img ? (img.getAttribute('alt') || '').trim() : '';
            var links = Array.from(card.querySelectorAll(':scope > a'));
            var keep = links.find(function (a) { return a.classList.contains('mouser-only-product-name'); }) || links[0];
            if (!keep && title) {
                keep = document.createElement('a');
                keep.href = '#';
                keep.className = 'mouser-only-product-name';
                keep.textContent = title;
                card.appendChild(keep);
            }
            if (keep) {
                if (!keep.textContent.trim() && title) keep.textContent = title;
                keep.className = 'mouser-only-product-name';
                links.forEach(function (a) { if (a !== keep) a.remove(); });
                card.appendChild(keep); // always keep below image, not inside image area
            }
        });
    }
    if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', enforceOneNewestProductName);
    else enforceOneNewestProductName();
    window.setTimeout(enforceOneNewestProductName, 300);
    window.setTimeout(enforceOneNewestProductName, 1000);
    window.setTimeout(enforceOneNewestProductName, 2000);
})();


/* Mouser product enlarge modal: robust open/close like original site */
(function () {
    function getModal() {
        return document.getElementById('stellar-enlarge');
    }

    function openModal() {
        var modal = getModal();
        if (!modal) return;
        modal.classList.add('is-open');
        document.documentElement.classList.add('mouser-modal-open');
    }

    function closeModal(evt) {
        if (evt) {
            evt.preventDefault();
            evt.stopPropagation();
        }
        var modal = getModal();
        if (!modal) return;
        modal.classList.remove('is-open');
        document.documentElement.classList.remove('mouser-modal-open');

        // Remove #stellar-enlarge from the address bar, so clicking Enlarge again works immediately.
        if (window.location.hash === '#stellar-enlarge' || window.location.hash === '#modal-closed') {
            history.replaceState(null, document.title, window.location.pathname + window.location.search);
        }
    }

    function syncModalFromHash() {
        if (window.location.hash === '#stellar-enlarge') {
            openModal();
        } else {
            var modal = getModal();
            if (modal) modal.classList.remove('is-open');
            document.documentElement.classList.remove('mouser-modal-open');
        }
    }

    function bindModal() {
        document.querySelectorAll('a[href="#stellar-enlarge"]').forEach(function (link) {
            link.addEventListener('click', function (evt) {
                evt.preventDefault();
                history.replaceState(null, document.title, window.location.pathname + window.location.search + '#stellar-enlarge');
                openModal();
            });
        });

        document.querySelectorAll('.stellar-modal-overlay .modal-close, .stellar-modal-overlay .modal-bg-close').forEach(function (link) {
            link.setAttribute('href', '#');
            link.addEventListener('click', closeModal);
        });

        document.addEventListener('keydown', function (evt) {
            if (evt.key === 'Escape') closeModal(evt);
        });

        window.addEventListener('hashchange', syncModalFromHash);
        syncModalFromHash();
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', bindModal);
    } else {
        bindModal();
    }
})();

(function () {
    "use strict";

    function initManufacturerAnchorScroll() {
        const page = document.querySelector(".mouser-manufacturer-detail-page");
        if (!page || page.dataset.anchorScrollReady === "1") {
            return;
        }
        page.dataset.anchorScrollReady = "1";

        const tabLinks = page.querySelectorAll(".manufacturer-side-tabs a[href^='#']");
        tabLinks.forEach((link) => {
            link.addEventListener("click", function (ev) {
                const target = page.querySelector(this.getAttribute("href"));
                if (!target) {
                    return;
                }
                ev.preventDefault();
                tabLinks.forEach((item) => item.classList.remove("active"));
                this.classList.add("active");
                target.scrollIntoView({ behavior: "smooth", block: "start" });
            });
        });
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", initManufacturerAnchorScroll);
    } else {
        initManufacturerAnchorScroll();
    }
    window.setTimeout(initManufacturerAnchorScroll, 500);
    window.setTimeout(initManufacturerAnchorScroll, 1500);
})();

(function () {
    "use strict";

    function initMouserOrderPreference() {
        const popup = document.querySelector("#mouserOrderPreference");
        if (!popup || popup.dataset.orderPrefReady === "1") {
            return;
        }
        popup.dataset.orderPrefReady = "1";

        const savedPreference = window.localStorage && window.localStorage.getItem("mouser_order_preference");
        if (savedPreference) {
            popup.classList.add("is-hidden");
            return;
        }

        const closePopup = function () {
            popup.classList.add("is-hidden");
        };

        const closeBtn = popup.querySelector(".mouser-order-pref-close");
        const cancelBtn = popup.querySelector(".mouser-order-pref-cancel");
        const saveBtn = popup.querySelector(".mouser-order-pref-save");

        if (closeBtn) {
            closeBtn.addEventListener("click", closePopup);
        }
        if (cancelBtn) {
            cancelBtn.addEventListener("click", closePopup);
        }
        if (saveBtn) {
            saveBtn.addEventListener("click", function () {
                const selected = popup.querySelector("input[name='mouser_order_preference']:checked");
                if (selected && window.localStorage) {
                    window.localStorage.setItem("mouser_order_preference", selected.value);
                }
                closePopup();
            });
        }

        popup.addEventListener("click", function (ev) {
            if (ev.target === popup) {
                closePopup();
            }
        });
        document.addEventListener("keydown", function (ev) {
            if (ev.key === "Escape") {
                closePopup();
            }
        });
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", initMouserOrderPreference);
    } else {
        initMouserOrderPreference();
    }
    window.setTimeout(initMouserOrderPreference, 500);
})();

/* === FINAL SCROLLING BANNER FIX: stable Mouser-style autoplay slider === */
(function () {
    "use strict";

    function initFinalMouserScrollingBanner() {
        var slider = document.querySelector(".mouser-homepage .mouser-home-slider");
        if (!slider || slider.dataset.finalSliderReady === "1") return;
        slider.dataset.finalSliderReady = "1";

        var slides = Array.prototype.slice.call(slider.querySelectorAll(".mh-slide"));
        var dots = Array.prototype.slice.call(slider.querySelectorAll(".mh-dot"));
        var pauseBtn = slider.querySelector(".mh-pause");
        if (!slides.length) return;

        // Stop older slider code from fighting with this one.
        slider.dataset.sliderReady = "1";

        var current = slides.findIndex(function (s) { return s.classList.contains("active"); });
        if (current < 0) current = 0;
        var paused = false;
        var timer = null;
        var interval = parseInt(slider.getAttribute("data-interval") || "4000", 10);

        function paint(index) {
            current = (index + slides.length) % slides.length;
            slides.forEach(function (slide, i) {
                slide.classList.toggle("active", i === current);
                slide.setAttribute("aria-hidden", i === current ? "false" : "true");
            });
            dots.forEach(function (dot, i) {
                dot.classList.toggle("active", i === current);
                dot.setAttribute("aria-current", i === current ? "true" : "false");
            });
        }

        function play() {
            if (timer) window.clearInterval(timer);
            timer = window.setInterval(function () {
                if (!paused) paint(current + 1);
            }, interval);
        }

        dots.forEach(function (dot) {
            dot.addEventListener("click", function (ev) {
                ev.preventDefault();
                var target = parseInt(dot.getAttribute("data-slide") || "0", 10);
                paint(target);
                play();
            });
        });

        if (pauseBtn) {
            pauseBtn.addEventListener("click", function (ev) {
                ev.preventDefault();
                paused = !paused;
                var icon = pauseBtn.querySelector("i");
                if (icon) icon.className = paused ? "fa fa-play" : "fa fa-pause";
                pauseBtn.setAttribute("aria-label", paused ? "Play slideshow" : "Pause slideshow");
            });
        }

        // Keep scrolling like the real homepage; do not pause on hover.
        paint(current);
        play();
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", initFinalMouserScrollingBanner);
    } else {
        initFinalMouserScrollingBanner();
    }
    window.setTimeout(initFinalMouserScrollingBanner, 600);
    window.setTimeout(initFinalMouserScrollingBanner, 1600);
})();

(function () {
    "use strict";

    function initNewManufacturersViewMore() {
        const page = document.querySelector(".mouser-new-manufacturers-page");
        if (!page || page.dataset.newManufacturersReady === "1") {
            return;
        }
        page.dataset.newManufacturersReady = "1";

        const items = Array.from(page.querySelectorAll(".new-manufacturer-item"));
        const button = page.querySelector(".new-view-more-btn");
        const wrap = page.querySelector(".new-view-more-wrap");
        const batchSize = 10;

        if (!button || !wrap || !items.length) {
            return;
        }

        function hiddenItems() {
            return items.filter((item) => item.classList.contains("new-manufacturer-hidden"));
        }

        function refreshButton() {
            if (hiddenItems().length === 0) {
                wrap.style.display = "none";
            } else {
                wrap.style.display = "block";
            }
        }

        button.addEventListener("click", function () {
            hiddenItems().slice(0, batchSize).forEach((item) => {
                item.classList.remove("new-manufacturer-hidden");
            });
            refreshButton();
        });

        refreshButton();
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", initNewManufacturersViewMore);
    } else {
        initNewManufacturersViewMore();
    }
    window.setTimeout(initNewManufacturersViewMore, 500);
    window.setTimeout(initNewManufacturersViewMore, 1500);
})();

// ── Account & Orders + Cart Dropdowns ────────────────────────────────────────
(function initMouserDropdowns() {
    "use strict";

    function setup() {
        var accBtn  = document.getElementById('mouserAccountBtn');
        var accDrop = document.getElementById('mouserAccountDropdown');
        var cartBtn  = document.getElementById('mouserCartBtn');
        var cartDrop = document.getElementById('mouserCartDropdown');

        if (!accBtn || !accDrop) return;

        function closeAll() {
            accDrop.classList.remove('open');
            accBtn.classList.remove('open');
            if (cartDrop && cartBtn) {
                cartDrop.classList.remove('open');
                cartBtn.classList.remove('open');
            }
        }

        accBtn.addEventListener('click', function (e) {
            e.preventDefault();
            e.stopPropagation();
            var isOpen = accDrop.classList.contains('open');
            closeAll();
            if (!isOpen) {
                accDrop.classList.add('open');
                accBtn.classList.add('open');
            }
        });

        if (cartBtn && cartDrop) {
            cartBtn.addEventListener('click', function (e) {
                e.preventDefault();
                e.stopPropagation();
                var isOpen = cartDrop.classList.contains('open');
                closeAll();
                if (!isOpen) {
                    cartDrop.classList.add('open');
                    cartBtn.classList.add('open');
                }
            });
        }

        // Close when clicking outside either dropdown
        document.addEventListener('click', function (e) {
            if (!e.target.closest('.mh-account-wrap') &&
                !e.target.closest('.mh-cart-wrap')) {
                closeAll();
            }
        });

        // Close on Escape key
        document.addEventListener('keydown', function (e) {
            if (e.key === 'Escape') closeAll();
        });
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', setup);
    } else {
        setup();
    }
})();

// ── Login page header dropdowns (separate IDs to avoid conflicts) ─────────────
(function initLoginPageDropdowns() {
    "use strict";
    function setup() {
        var accBtn  = document.getElementById('mouserAccountBtnLogin');
        var accDrop = document.getElementById('mouserAccountDropdownLogin');
        var cartBtn  = document.getElementById('mouserCartBtnLogin');
        var cartDrop = document.getElementById('mouserCartDropdownLogin');
        if (!accBtn || !accDrop) return;

        function closeAll() {
            accDrop.classList.remove('open'); accBtn.classList.remove('open');
            if (cartDrop && cartBtn) { cartDrop.classList.remove('open'); cartBtn.classList.remove('open'); }
        }
        accBtn.addEventListener('click', function(e) {
            e.preventDefault(); e.stopPropagation();
            var open = accDrop.classList.contains('open'); closeAll();
            if (!open) { accDrop.classList.add('open'); accBtn.classList.add('open'); }
        });
        if (cartBtn && cartDrop) {
            cartBtn.addEventListener('click', function(e) {
                e.preventDefault(); e.stopPropagation();
                var open = cartDrop.classList.contains('open'); closeAll();
                if (!open) { cartDrop.classList.add('open'); cartBtn.classList.add('open'); }
            });
        }
        document.addEventListener('click', function(e) {
            if (!e.target.closest('#mouserAccountBtnLogin') && !e.target.closest('#mouserAccountDropdownLogin') &&
                !e.target.closest('#mouserCartBtnLogin') && !e.target.closest('#mouserCartDropdownLogin')) closeAll();
        });
        document.addEventListener('keydown', function(e) { if (e.key === 'Escape') closeAll(); });
    }
    if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', setup);
    else setup();
})();

// ── Forgot Username / Password page dropdowns ─────────────────────────────────
(function initForgotPageDropdowns() {
    "use strict";
    var pairs = [
        ['mouserAccBtnFU', 'mouserAccDropFU', 'mouserCartBtnFU', 'mouserCartDropFU'],
        ['mouserAccBtnFP', 'mouserAccDropFP', 'mouserCartBtnFP', 'mouserCartDropFP'],
    ];
    function setup() {
        pairs.forEach(function(ids) {
            var accBtn = document.getElementById(ids[0]);
            var accDrop = document.getElementById(ids[1]);
            var cartBtn = document.getElementById(ids[2]);
            var cartDrop = document.getElementById(ids[3]);
            if (!accBtn || !accDrop) return;

            function closeAll() {
                accDrop.classList.remove('open'); accBtn.classList.remove('open');
                if (cartDrop && cartBtn) { cartDrop.classList.remove('open'); cartBtn.classList.remove('open'); }
            }
            accBtn.addEventListener('click', function(e) {
                e.preventDefault(); e.stopPropagation();
                var open = accDrop.classList.contains('open'); closeAll();
                if (!open) { accDrop.classList.add('open'); accBtn.classList.add('open'); }
            });
            if (cartBtn && cartDrop) {
                cartBtn.addEventListener('click', function(e) {
                    e.preventDefault(); e.stopPropagation();
                    var open = cartDrop.classList.contains('open'); closeAll();
                    if (!open) { cartDrop.classList.add('open'); cartBtn.classList.add('open'); }
                });
            }
            document.addEventListener('click', function(e) {
                if (!e.target.closest('#' + ids[0]) && !e.target.closest('#' + ids[1]) &&
                    !e.target.closest('#' + ids[2]) && !e.target.closest('#' + ids[3])) closeAll();
            });
            document.addEventListener('keydown', function(e) { if (e.key === 'Escape') closeAll(); });
        });
    }
    if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', setup);
    else setup();
})();

// ── Order History page dropdowns ──────────────────────────────────────────────
(function initOrderHistoryDropdowns() {
    "use strict";
    function setup() {
        var accBtn = document.getElementById('mouserAccBtnOH');
        var accDrop = document.getElementById('mouserAccDropOH');
        var cartBtn = document.getElementById('mouserCartBtnOH');
        var cartDrop = document.getElementById('mouserCartDropOH');
        if (!accBtn || !accDrop) return;
        function closeAll() {
            accDrop.classList.remove('open'); accBtn.classList.remove('open');
            if (cartDrop && cartBtn) { cartDrop.classList.remove('open'); cartBtn.classList.remove('open'); }
        }
        accBtn.addEventListener('click', function(e) {
            e.preventDefault(); e.stopPropagation();
            var open = accDrop.classList.contains('open'); closeAll();
            if (!open) { accDrop.classList.add('open'); accBtn.classList.add('open'); }
        });
        if (cartBtn && cartDrop) {
            cartBtn.addEventListener('click', function(e) {
                e.preventDefault(); e.stopPropagation();
                var open = cartDrop.classList.contains('open'); closeAll();
                if (!open) { cartDrop.classList.add('open'); cartBtn.classList.add('open'); }
            });
        }
        document.addEventListener('click', function(e) {
            if (!e.target.closest('#mouserAccBtnOH') && !e.target.closest('#mouserAccDropOH') &&
                !e.target.closest('#mouserCartBtnOH') && !e.target.closest('#mouserCartDropOH')) closeAll();
        });
        document.addEventListener('keydown', function(e) { if (e.key === 'Escape') closeAll(); });
    }
    if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', setup);
    else setup();
})();

// ── Register page header dropdowns ───────────────────────────────────────────
(function initRegisterDropdowns() {
    "use strict";
    function setup() {
        var accBtn  = document.getElementById('mouserAccBtnReg');
        var accDrop = document.getElementById('mouserAccDropReg');
        var cartBtn  = document.getElementById('mouserCartBtnReg');
        var cartDrop = document.getElementById('mouserCartDropReg');
        if (!accBtn || !accDrop) return;
        function closeAll() {
            accDrop.classList.remove('open'); accBtn.classList.remove('open');
            if (cartDrop && cartBtn) { cartDrop.classList.remove('open'); cartBtn.classList.remove('open'); }
        }
        accBtn.addEventListener('click', function(e) {
            e.preventDefault(); e.stopPropagation();
            var open = accDrop.classList.contains('open'); closeAll();
            if (!open) { accDrop.classList.add('open'); accBtn.classList.add('open'); }
        });
        if (cartBtn && cartDrop) {
            cartBtn.addEventListener('click', function(e) {
                e.preventDefault(); e.stopPropagation();
                var open = cartDrop.classList.contains('open'); closeAll();
                if (!open) { cartDrop.classList.add('open'); cartBtn.classList.add('open'); }
            });
        }
        document.addEventListener('click', function(e) {
            if (!e.target.closest('#mouserAccBtnReg') && !e.target.closest('#mouserAccDropReg') &&
                !e.target.closest('#mouserCartBtnReg') && !e.target.closest('#mouserCartDropReg')) closeAll();
        });
        document.addEventListener('keydown', function(e) { if (e.key === 'Escape') closeAll(); });
    }
    if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', setup);
    else setup();
})();

// ── Search "All" filter dropdown ───────────────────────────────────────────
(function () {
    function setup() {
        var btn = document.getElementById('mh-search-filter-btn');
        var panel = document.getElementById('mh-search-filter-panel');
        if (!btn || !panel) return;

        // Toggle panel on button click
        btn.addEventListener('click', function (e) {
            e.stopPropagation();
            var isOpen = panel.style.display === 'block';
            panel.style.display = isOpen ? 'none' : 'block';
            btn.setAttribute('aria-expanded', String(!isOpen));
        });

        // Select a category: update button label, close panel
        panel.querySelectorAll('a[data-filter]').forEach(function (a) {
            a.addEventListener('click', function (e) {
                e.preventDefault();
                btn.innerHTML = a.getAttribute('data-filter') + ' <i class="fa fa-angle-down"></i>';
                panel.style.display = 'none';
                btn.setAttribute('aria-expanded', 'false');
                var input = document.getElementById('mh-search-input');
                if (input) input.focus();
            });
        });

        // Close when clicking outside
        document.addEventListener('click', function (e) {
            if (!btn.contains(e.target) && !panel.contains(e.target)) {
                panel.style.display = 'none';
                btn.setAttribute('aria-expanded', 'false');
            }
        });

        // Close on Escape
        document.addEventListener('keydown', function (e) {
            if (e.key === 'Escape') {
                panel.style.display = 'none';
                btn.setAttribute('aria-expanded', 'false');
            }
        });
    }
    if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', setup);
    else setup();
})();




(function () {
    "use strict";

    function initMouserAutocomplete() {
        const input = document.getElementById("mh-search-input");
        const wrap = document.querySelector(".mh-search-wrap");

        if (!input || !wrap || input.dataset.autoReady === "1") {
            return;
        }

        input.dataset.autoReady = "1";

        const manufacturers = [
            "Panasonic",
            "Panjit",
            "Parallax",
            "Phoenix Contact",
            "Pimoroni",
            "STMicroelectronics",
            "Texas Instruments",
            "Infineon",
            "Murata",
            "Littelfuse",
            "Sensirion",
            "TE Connectivity",
            "Vishay",
            "Amphenol"
        ];

        const panel = document.createElement("div");
        panel.className = "mh-autocomplete-panel";
        panel.style.display = "none";

        wrap.appendChild(panel);

        input.addEventListener("input", function () {
            const value = this.value.toLowerCase().trim();

            if (!value) {
                panel.style.display = "none";
                return;
            }

            const filtered = manufacturers.filter(m =>
                m.toLowerCase().includes(value)
            );

            if (!filtered.length) {
                panel.style.display = "none";
                return;
            }

            panel.innerHTML = `
                <div class="mh-autocomplete-title">Manufacturer</div>
                ${filtered.map(item => `
                    <div class="mh-autocomplete-item">${item}</div>
                `).join("")}
            `;

            panel.style.display = "block";

            panel.querySelectorAll(".mh-autocomplete-item").forEach(el => {
                el.addEventListener("click", function () {
                    const selectedManufacturer = this.textContent.trim();
                    input.value = selectedManufacturer;
                    panel.style.display = "none";

                    // Redirect like original Mouser website
                    window.location.href = "/c/?m=" + encodeURIComponent(selectedManufacturer);
                });
            });

            // Handle Enter key search
            input.addEventListener("keydown", function (e) {
                if (e.key === "Enter") {
                    const keyword = input.value.trim();
                    if (keyword) {
                        window.location.href = "/c/?m=" + encodeURIComponent(keyword);
                    }
                }
            });
        });

        document.addEventListener("click", function (e) {
            if (!wrap.contains(e.target)) {
                panel.style.display = "none";
            }
        });
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", initMouserAutocomplete);
    } else {
        initMouserAutocomplete();
    }

    window.setTimeout(initMouserAutocomplete, 1000);
})();


document.addEventListener("DOMContentLoaded", function () {
    const mf = document.getElementById("manufacturer_filter");
    if(mf){
        mf.size = 1;
        mf.style.display = "inline-block";
    }
});
