/** @odoo-module **/

import { Message } from "@mail/core/common/message";
import { rpc } from "@web/core/network/rpc";
import { patch } from "@web/core/utils/patch";

/**
 * EXTENSION of the same core Message component portal_rating already
 * patches. Adds vote handling + lightbox for review media thumbnails.
 */
patch(Message.prototype, {
    /**
     * Cast/toggle a helpful or unhelpful vote on a product review.
     * @param {"helpful"|"unhelpful"} voteType
     */
    async onVoteReview(voteType) {
        const ratingId = this.message.rating_id && this.message.rating_id.id;
        if (!ratingId) {
            return;
        }
        const result = await rpc("/website_sale/review/vote", {
            rating_id: ratingId,
            vote_type: voteType,
        });
        if (result && !result.error) {
            Object.assign(this.message.rating_id, {
                helpful_count: result.helpful_count,
                unhelpful_count: result.unhelpful_count,
                user_vote: result.user_vote,
            });
        }
    },

    /**
     * Open a simple vanilla lightbox for a review media item.
     * Avoids pulling in an OWL dialog dependency for a one-off viewer.
     */
    onWsreOpenLightbox(att, attachments) {
        const items = (attachments || []).filter((a) => a.is_image || a.is_video);
        if (!items.length) {
            return;
        }
        let index = Math.max(0, items.findIndex((a) => a.id === att.id));

        // Remove any existing lightbox
        document.querySelectorAll(".o_wsre_lightbox").forEach((el) => el.remove());

        const overlay = document.createElement("div");
        overlay.className = "o_wsre_lightbox";
        overlay.setAttribute("role", "dialog");
        overlay.setAttribute("aria-modal", "true");
        Object.assign(overlay.style, {
            position: "fixed",
            inset: "0",
            zIndex: "1055",
            background: "rgba(0,0,0,0.85)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            flexDirection: "column",
            padding: "1rem",
        });

        const content = document.createElement("div");
        content.style.cssText = "max-width:90vw;max-height:80vh;position:relative;";

        const caption = document.createElement("div");
        caption.style.cssText = "color:#fff;margin-top:0.75rem;font-size:0.9rem;text-align:center;";

        const closeBtn = document.createElement("button");
        closeBtn.type = "button";
        closeBtn.innerHTML = "&times;";
        closeBtn.setAttribute("aria-label", "Close");
        Object.assign(closeBtn.style, {
            position: "absolute",
            top: "12px",
            right: "16px",
            background: "transparent",
            border: "none",
            color: "#fff",
            fontSize: "2rem",
            cursor: "pointer",
            lineHeight: "1",
            zIndex: "1",
        });

        const prevBtn = document.createElement("button");
        prevBtn.type = "button";
        prevBtn.innerHTML = "&#10094;";
        prevBtn.setAttribute("aria-label", "Previous");
        Object.assign(prevBtn.style, {
            position: "absolute",
            left: "8px",
            top: "50%",
            transform: "translateY(-50%)",
            background: "rgba(0,0,0,0.4)",
            border: "none",
            color: "#fff",
            fontSize: "1.75rem",
            cursor: "pointer",
            padding: "0.5rem 0.75rem",
            borderRadius: "4px",
        });

        const nextBtn = document.createElement("button");
        nextBtn.type = "button";
        nextBtn.innerHTML = "&#10095;";
        nextBtn.setAttribute("aria-label", "Next");
        Object.assign(nextBtn.style, {
            position: "absolute",
            right: "8px",
            top: "50%",
            transform: "translateY(-50%)",
            background: "rgba(0,0,0,0.4)",
            border: "none",
            color: "#fff",
            fontSize: "1.75rem",
            cursor: "pointer",
            padding: "0.5rem 0.75rem",
            borderRadius: "4px",
        });

        function render() {
            const item = items[index];
            content.innerHTML = "";
            if (item.is_image) {
                const img = document.createElement("img");
                img.src = item.url + (item.access_token && !item.url.includes("access_token")
                    ? (item.url.includes("?") ? "&" : "?") + "access_token=" + item.access_token
                    : "");
                img.alt = item.name || "";
                img.style.cssText = "max-width:90vw;max-height:80vh;object-fit:contain;display:block;margin:0 auto;";
                content.appendChild(img);
            } else if (item.is_video) {
                const video = document.createElement("video");
                video.src = item.url + (item.access_token && !item.url.includes("access_token")
                    ? (item.url.includes("?") ? "&" : "?") + "access_token=" + item.access_token
                    : "");
                video.controls = true;
                video.autoplay = true;
                video.style.cssText = "max-width:90vw;max-height:80vh;display:block;margin:0 auto;";
                content.appendChild(video);
            }
            caption.textContent = (item.name || "") + (items.length > 1 ? ` (${index + 1}/${items.length})` : "");
            prevBtn.style.display = items.length > 1 ? "" : "none";
            nextBtn.style.display = items.length > 1 ? "" : "none";
        }

        function close() {
            overlay.remove();
            document.removeEventListener("keydown", onKey);
        }
        function onKey(ev) {
            if (ev.key === "Escape") close();
            if (ev.key === "ArrowLeft") { index = (index - 1 + items.length) % items.length; render(); }
            if (ev.key === "ArrowRight") { index = (index + 1) % items.length; render(); }
        }

        closeBtn.addEventListener("click", close);
        prevBtn.addEventListener("click", () => { index = (index - 1 + items.length) % items.length; render(); });
        nextBtn.addEventListener("click", () => { index = (index + 1) % items.length; render(); });
        overlay.addEventListener("click", (ev) => { if (ev.target === overlay) close(); });
        document.addEventListener("keydown", onKey);

        overlay.appendChild(closeBtn);
        overlay.appendChild(prevBtn);
        overlay.appendChild(nextBtn);
        overlay.appendChild(content);
        overlay.appendChild(caption);
        document.body.appendChild(overlay);
        render();
    },
});
