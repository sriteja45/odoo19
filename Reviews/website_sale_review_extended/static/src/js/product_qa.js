/** @odoo-module **/

import { rpc } from "@web/core/network/rpc";
import { whenReady } from "@odoo/owl";

/**
 * Product page Q&A section (Phase 3).
 * Renders questions/answers, handles ask / answer / upvote.
 */

function escapeHtml(str) {
    const d = document.createElement("div");
    d.textContent = str || "";
    return d.innerHTML;
}

function formatDate(iso) {
    if (!iso) return "";
    try {
        const d = new Date(iso);
        return d.toLocaleDateString(undefined, { year: "numeric", month: "short", day: "numeric" });
    } catch {
        return iso;
    }
}

function renderAnswer(a) {
    const badges = [];
    if (a.is_seller) {
        badges.push(`<span class="badge text-bg-primary ms-1">Seller</span>`);
    }
    if (a.is_verified_buyer) {
        badges.push(`<span class="badge text-bg-success ms-1">Verified Buyer</span>`);
    }
    return `
        <div class="o_wsre_qa_answer border-start border-3 ps-3 mb-2" data-answer-id="${a.id}">
            <div class="small text-muted mb-1">
                <strong>${escapeHtml(a.author)}</strong>${badges.join("")}
                <span class="ms-2">${formatDate(a.create_date)}</span>
            </div>
            <div class="mb-1">${escapeHtml(a.body)}</div>
            <button type="button"
                    class="btn btn-sm btn-link p-0 o_wsre_qa_upvote_answer ${a.user_voted ? "fw-bold" : ""}"
                    data-answer-id="${a.id}">
                <i class="fa fa-thumbs-o-up me-1"></i>
                <span class="o_wsre_qa_upvote_count">${a.upvote_count || 0}</span>
            </button>
        </div>
    `;
}

function renderQuestion(q, isLoggedIn) {
    const answersHtml = (q.answers || []).map(renderAnswer).join("");
    const answerForm = isLoggedIn
        ? `
        <div class="o_wsre_qa_answer_form mt-2 mb-2 d-none" data-question-id="${q.id}">
            <textarea class="form-control form-control-sm mb-1 o_wsre_qa_answer_body" rows="2"
                      placeholder="Write your answer…"></textarea>
            <button type="button" class="btn btn-sm btn-outline-primary o_wsre_qa_answer_submit"
                    data-question-id="${q.id}">Post answer</button>
            <span class="o_wsre_qa_answer_error text-danger small ms-2"></span>
        </div>
        <button type="button" class="btn btn-sm btn-link p-0 o_wsre_qa_answer_toggle"
                data-question-id="${q.id}">Answer this question</button>
        `
        : "";
    return `
        <div class="o_wsre_qa_item card mb-3" data-question-id="${q.id}">
            <div class="card-body">
                <div class="d-flex justify-content-between align-items-start gap-2">
                    <div>
                        <div class="fw-semibold">${escapeHtml(q.name)}</div>
                        ${q.body ? `<div class="text-muted small mt-1">${escapeHtml(q.body)}</div>` : ""}
                        <div class="small text-muted mt-1">
                            Asked by ${escapeHtml(q.author)} · ${formatDate(q.create_date)}
                            ${q.state === "answered" ? '<span class="badge text-bg-success ms-1">Answered</span>' : ""}
                        </div>
                    </div>
                    <button type="button"
                            class="btn btn-sm btn-outline-secondary o_wsre_qa_upvote_question ${q.user_voted ? "active" : ""}"
                            data-question-id="${q.id}" title="Upvote">
                        <i class="fa fa-chevron-up"></i>
                        <span class="o_wsre_qa_upvote_count">${q.upvote_count || 0}</span>
                    </button>
                </div>
                <div class="o_wsre_qa_answers mt-3">
                    ${answersHtml || '<div class="text-muted small">No answers yet.</div>'}
                </div>
                ${answerForm}
            </div>
        </div>
    `;
}

async function loadQuestions(section) {
    const tmplId = parseInt(section.getAttribute("data-product-tmpl-id"), 10);
    const listEl = section.querySelector(".o_wsre_qa_list");
    const countEl = section.querySelector(".o_wsre_qa_count");
    const isLoggedIn = section.getAttribute("data-is-logged") === "1";
    if (!tmplId || !listEl) return;

    listEl.innerHTML = `<div class="text-muted small o_wsre_qa_loading">Loading questions…</div>`;
    let result;
    try {
        result = await rpc("/website_sale/question/list", {
            product_tmpl_id: tmplId,
            limit: 30,
            offset: 0,
        });
    } catch (e) {
        listEl.innerHTML = `<div class="text-danger small">Could not load questions.</div>`;
        return;
    }
    if (!result?.ok) {
        listEl.innerHTML = `<div class="text-danger small">${escapeHtml(result?.error || "Error")}</div>`;
        return;
    }
    if (countEl) {
        countEl.textContent = result.total ? String(result.total) : "";
        countEl.classList.toggle("d-none", !result.total);
    }
    if (!result.questions?.length) {
        listEl.innerHTML = `<div class="text-muted">No questions yet. Be the first to ask!</div>`;
        return;
    }
    listEl.innerHTML = result.questions.map((q) => renderQuestion(q, isLoggedIn)).join("");
}

function bindEvents(section) {
    const tmplId = parseInt(section.getAttribute("data-product-tmpl-id"), 10);
    const isLoggedIn = section.getAttribute("data-is-logged") === "1";

    // Ask
    const submitBtn = section.querySelector(".o_wsre_qa_submit");
    if (submitBtn) {
        submitBtn.addEventListener("click", async () => {
            const name = section.querySelector(".o_wsre_qa_name")?.value?.trim() || "";
            const body = section.querySelector(".o_wsre_qa_body")?.value?.trim() || "";
            const isAnonymous = !!section.querySelector(".o_wsre_qa_anonymous")?.checked;
            const errEl = section.querySelector(".o_wsre_qa_ask_error");
            if (errEl) errEl.textContent = "";
            if (name.length < 5) {
                if (errEl) errEl.textContent = "Please write at least 5 characters.";
                return;
            }
            submitBtn.disabled = true;
            try {
                const result = await rpc("/website_sale/question/ask", {
                    product_tmpl_id: tmplId,
                    name,
                    body,
                    is_anonymous: isAnonymous,
                });
                if (!result?.ok) {
                    if (errEl) errEl.textContent = result?.error || "Failed to submit.";
                    return;
                }
                section.querySelector(".o_wsre_qa_name").value = "";
                if (section.querySelector(".o_wsre_qa_body")) {
                    section.querySelector(".o_wsre_qa_body").value = "";
                }
                await loadQuestions(section);
            } catch (e) {
                if (errEl) errEl.textContent = "Failed to submit.";
            } finally {
                submitBtn.disabled = false;
            }
        });
    }

    // Delegated: upvote question / answer, answer toggle / submit
    section.addEventListener("click", async (ev) => {
        const upQ = ev.target.closest(".o_wsre_qa_upvote_question");
        if (upQ) {
            if (!isLoggedIn) return;
            const qid = parseInt(upQ.getAttribute("data-question-id"), 10);
            try {
                const result = await rpc("/website_sale/question/upvote", { question_id: qid });
                if (result?.ok) {
                    upQ.querySelector(".o_wsre_qa_upvote_count").textContent = result.upvote_count;
                    upQ.classList.toggle("active", !!result.user_voted);
                }
            } catch (_) {}
            return;
        }

        const upA = ev.target.closest(".o_wsre_qa_upvote_answer");
        if (upA) {
            if (!isLoggedIn) return;
            const aid = parseInt(upA.getAttribute("data-answer-id"), 10);
            try {
                const result = await rpc("/website_sale/question/upvote", { answer_id: aid });
                if (result?.ok) {
                    upA.querySelector(".o_wsre_qa_upvote_count").textContent = result.upvote_count;
                    upA.classList.toggle("fw-bold", !!result.user_voted);
                }
            } catch (_) {}
            return;
        }

        const toggle = ev.target.closest(".o_wsre_qa_answer_toggle");
        if (toggle) {
            const qid = toggle.getAttribute("data-question-id");
            const form = section.querySelector(`.o_wsre_qa_answer_form[data-question-id="${qid}"]`);
            if (form) form.classList.toggle("d-none");
            return;
        }

        const ansSubmit = ev.target.closest(".o_wsre_qa_answer_submit");
        if (ansSubmit) {
            if (!isLoggedIn) return;
            const qid = parseInt(ansSubmit.getAttribute("data-question-id"), 10);
            const form = section.querySelector(`.o_wsre_qa_answer_form[data-question-id="${qid}"]`);
            const body = form?.querySelector(".o_wsre_qa_answer_body")?.value?.trim() || "";
            const errEl = form?.querySelector(".o_wsre_qa_answer_error");
            if (errEl) errEl.textContent = "";
            if (body.length < 2) {
                if (errEl) errEl.textContent = "Answer is too short.";
                return;
            }
            ansSubmit.disabled = true;
            try {
                const result = await rpc("/website_sale/question/answer", {
                    question_id: qid,
                    body,
                });
                if (!result?.ok) {
                    if (errEl) errEl.textContent = result?.error || "Failed.";
                    return;
                }
                await loadQuestions(section);
            } catch (_) {
                if (errEl) errEl.textContent = "Failed.";
            } finally {
                ansSubmit.disabled = false;
            }
        }
    });
}

function boot() {
    document.querySelectorAll(".o_wsre_qa_section").forEach((section) => {
        bindEvents(section);
        loadQuestions(section);
    });
}

whenReady(() => {
    setTimeout(boot, 200);
});
