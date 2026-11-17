/** @odoo-module **/

console.log("QEVRIXA BLOG CHAT JS LOADED");

(function () {
    "use strict";

    // ============================================================
    // CONFIGURATION
    // ============================================================

    const CREATE_JOB_URL = "/blog/admin/chat";
    const STATUS_URL = "/blog/admin/chat/status";

    const STATUS_INTERVAL = 2000;
    const MAX_WAIT_TIME = 10 * 60 * 1000;


    // ============================================================
    // INTERNAL STATE
    // ============================================================

    let lastPath =
        window.location.pathname || "";

    let chatRoot = null;
    let chatButton = null;
    let chatWindow = null;
    let closeButton = null;
    let sendButton = null;
    let questionInput = null;
    let chatBody = null;


    // ============================================================
    // GET ADMIN CHAT ROOT
    // ============================================================

    function getAdminChatRoot() {

        return document.querySelector(
            "#qevrixa-blog-admin-chat"
        );
    }


    // ============================================================
    // GET CURRENT PATH
    // ============================================================

    function getCurrentPath() {

        return window.location.pathname || "";
    }


    // ============================================================
    // CHECK ODOO BACKEND
    // ============================================================

    function isOdooBackendPage() {

        return getCurrentPath().startsWith(
            "/odoo"
        );
    }


    // ============================================================
    // CHECK ADMIN BLOG CHAT
    // ============================================================

    function isBlogAdminPage() {

        const currentPath =
            getCurrentPath();

        const adminRoot =
            getAdminChatRoot();

        /*
         * The component root is the strongest indicator because
         * BlogAdminChat is mounted specifically for the admin
         * Blog Posts page.
         */

        const result =
            isOdooBackendPage() &&
            !!adminRoot;


        console.log(
            "QEVRIXA BLOG CHAT: CURRENT PATH:",
            currentPath
        );

        console.log(
            "QEVRIXA BLOG CHAT: ADMIN ROOT:",
            !!adminRoot
        );

        console.log(
            "QEVRIXA BLOG CHAT: ADMIN BLOG PAGE:",
            result
        );

        return result;
    }


    // ============================================================
    // FIND ADMIN CHAT ELEMENTS
    // ============================================================

    function getChatElements() {

        const root =
            getAdminChatRoot();

        if (!root) {

            return {
                root: null,
                chatButton: null,
                chatWindow: null,
                closeButton: null,
                sendButton: null,
                questionInput: null,
                chatBody: null,
            };
        }


        return {

            root,

            chatButton:
                root.querySelector(
                    "#blog-chat-button, " +
                    ".qevrixa-blog-chat-button"
                ),

            chatWindow:
                root.querySelector(
                    "#blog-chat-window, " +
                    ".qevrixa-blog-chat-window"
                ),

            closeButton:
                root.querySelector(
                    "#close-blog-chat, " +
                    ".qevrixa-blog-chat-close"
                ),

            sendButton:
                root.querySelector(
                    "#send-blog-question"
                ),

            questionInput:
                root.querySelector(
                    "#blog-question"
                ),

            chatBody:
                root.querySelector(
                    "#blog-chat-body, " +
                    ".qevrixa-blog-chat-body"
                ),
        };
    }


    // ============================================================
    // CLEAR CHAT REFERENCES
    // ============================================================

    function clearChatReferences() {

        chatRoot = null;
        chatButton = null;
        chatWindow = null;
        closeButton = null;
        sendButton = null;
        questionInput = null;
        chatBody = null;
    }


    // ============================================================
    // REMOVE ADMIN CHAT ONLY
    // ============================================================

    function removeChatFromNonAdminPage() {

        const adminRoot =
            getAdminChatRoot();

        if (adminRoot) {

            adminRoot.remove();
        }

        clearChatReferences();
    }


    // ============================================================
    // OPEN CHAT WINDOW
    // ============================================================

    function openChatWindow() {

        if (!chatWindow) {

            console.warn(
                "QEVRIXA BLOG CHAT: " +
                "Chat window reference is missing."
            );

            return;
        }


        console.log(
            "QEVRIXA BLOG CHAT: OPENING CHAT"
        );


        /*
         * display:block is enough to override the initial
         * template style="display:none".
         */

        chatWindow.style.display =
            "block";

        chatWindow.style.visibility =
            "visible";

        chatWindow.setAttribute(
            "aria-hidden",
            "false"
        );


        /*
         * Force the browser to recognize the state immediately.
         */

        void chatWindow.offsetWidth;


        setTimeout(
            function () {

                if (!questionInput) {
                    return;
                }

                try {

                    questionInput.focus();

                } catch (error) {

                    console.warn(
                        "QEVRIXA BLOG CHAT: " +
                        "Unable to focus input.",
                        error
                    );
                }

            },
            100
        );
    }


    // ============================================================
    // CLOSE CHAT WINDOW
    // ============================================================

    function closeChatWindow() {

        if (!chatWindow) {
            return;
        }


        console.log(
            "QEVRIXA BLOG CHAT: CLOSING CHAT"
        );


        chatWindow.style.display =
            "none";

        chatWindow.style.visibility =
            "hidden";

        chatWindow.setAttribute(
            "aria-hidden",
            "true"
        );
    }


    // ============================================================
    // INITIALIZE
    // ============================================================

    function initBlogChat() {

        console.log(
            "========================================"
        );

        console.log(
            "INIT QEVRIXA BLOG CHAT"
        );

        console.log(
            "========================================"
        );


        // --------------------------------------------------------
        // Only require Odoo backend here.
        // The admin OWL component itself identifies the Blog page.
        // --------------------------------------------------------

        if (!isOdooBackendPage()) {

            console.log(
                "QEVRIXA BLOG CHAT: " +
                "Not Odoo backend."
            );

            return false;
        }


        const elements =
            getChatElements();


        chatRoot =
            elements.root;

        chatButton =
            elements.chatButton;

        chatWindow =
            elements.chatWindow;

        closeButton =
            elements.closeButton;

        sendButton =
            elements.sendButton;

        questionInput =
            elements.questionInput;

        chatBody =
            elements.chatBody;


        // --------------------------------------------------------
        // REQUIRED ELEMENTS
        // --------------------------------------------------------

        if (
            !chatRoot ||
            !chatButton ||
            !chatWindow ||
            !sendButton ||
            !questionInput ||
            !chatBody
        ) {

            console.warn(
                "QEVRIXA BLOG CHAT: " +
                "Required Admin Chat elements not found.",
                {
                    root:
                        !!chatRoot,

                    button:
                        !!chatButton,

                    window:
                        !!chatWindow,

                    close:
                        !!closeButton,

                    send:
                        !!sendButton,

                    input:
                        !!questionInput,

                    body:
                        !!chatBody,
                }
            );

            return false;
        }


        // --------------------------------------------------------
        // DUPLICATE INITIALIZATION
        // --------------------------------------------------------

        if (
            chatButton.dataset.blogChatInitialized ===
            "true"
        ) {

            console.log(
                "QEVRIXA BLOG CHAT: " +
                "Already initialized."
            );

            return true;
        }


        chatButton.dataset.blogChatInitialized =
            "true";


        console.log(
            "QEVRIXA BLOG CHAT: " +
            "INITIALIZED SUCCESSFULLY."
        );


        // ========================================================
        // OPEN BUTTON
        // ========================================================

        chatButton.addEventListener(
            "click",
            function (event) {

                event.preventDefault();
                event.stopPropagation();


                /*
                 * Once this button exists inside the Admin OWL
                 * component, allow it to open.
                 */

                openChatWindow();
            }
        );


        // ========================================================
        // CLOSE BUTTON
        // ========================================================

        if (closeButton) {

            closeButton.addEventListener(
                "click",
                function (event) {

                    event.preventDefault();
                    event.stopPropagation();

                    closeChatWindow();
                }
            );
        }


        // ========================================================
        // SEND BUTTON
        // ========================================================

        sendButton.addEventListener(
            "click",
            function (event) {

                event.preventDefault();
                event.stopPropagation();

                sendMessage();
            }
        );


        // ========================================================
        // ENTER KEY
        // ========================================================

        questionInput.addEventListener(
            "keydown",
            function (event) {

                if (
                    event.key === "Enter" &&
                    !event.shiftKey
                ) {

                    event.preventDefault();

                    sendMessage();
                }
            }
        );


        return true;
    }


    // ============================================================
    // SEND MESSAGE
    // ============================================================

    async function sendMessage() {

        if (
            !chatRoot ||
            !chatButton ||
            !chatWindow ||
            !sendButton ||
            !questionInput ||
            !chatBody
        ) {

            console.warn(
                "QEVRIXA BLOG CHAT: " +
                "Chat is not initialized."
            );

            return;
        }


        const question =
            questionInput.value.trim();


        if (!question) {
            return;
        }


        if (sendButton.disabled) {
            return;
        }


        console.log(
            "========================================"
        );

        console.log(
            "QEVRIXA BLOG CHAT: NEW QUESTION"
        );

        console.log(
            "QUESTION:",
            question
        );

        console.log(
            "========================================"
        );


        appendUserMessage(
            question
        );


        questionInput.value =
            "";

        sendButton.disabled =
            true;


        const loadingId =
            "blog-chat-loading-" +
            Date.now();


        appendLoadingMessage(
            loadingId
        );


        try {

            // =====================================================
            // CREATE JOB
            // =====================================================

            console.log(
                "QEVRIXA BLOG CHAT: " +
                "Creating background job..."
            );


            const jobResult =
                await createChatJob(
                    question
                );


            console.log(
                "CHAT JOB RESULT:",
                jobResult
            );


            const jobId =
                getJobId(
                    jobResult
                );


            if (!jobId) {

                throw new Error(
                    "Odoo did not return a valid job ID."
                );
            }


            console.log(
                "QEVRIXA BLOG CHAT: JOB ID =",
                jobId
            );


            // =====================================================
            // POLL
            // =====================================================

            const finalResult =
                await waitForChatResult(
                    jobId,
                    loadingId
                );


            console.log(
                "FINAL CHAT RESULT:",
                finalResult
            );


            removeLoadingMessage(
                loadingId
            );


            if (!finalResult) {

                throw new Error(
                    "The chatbot returned an empty response."
                );
            }


            // =====================================================
            // ERROR
            // =====================================================

            if (
                isErrorStatus(
                    finalResult
                )
            ) {

                throw new Error(
                    getErrorMessage(
                        finalResult
                    )
                );
            }


            // =====================================================
            // EXTRACT ANSWER
            // =====================================================

            const answer =
                extractReply(
                    finalResult
                );


            if (
                !answer ||
                !String(answer).trim()
            ) {

                throw new Error(
                    "The chatbot completed but " +
                    "returned no displayable answer."
                );
            }


            appendBotMessage(
                answer
            );


            scrollChatToBottom();


            handleCreatedBlogs(
                finalResult
            );


        } catch (error) {

            console.error(
                "QEVRIXA BLOG CHAT ERROR:",
                error
            );


            removeLoadingMessage(
                loadingId
            );


            appendCustomError(
                error.message ||
                "Unable to get a response from the chatbot."
            );


            scrollChatToBottom();


        } finally {

            sendButton.disabled =
                false;


            setTimeout(
                function () {

                    try {

                        questionInput.focus();

                    } catch (error) {
                        // Ignore focus errors.
                    }

                },
                100
            );
        }
    }


    // ============================================================
    // HANDLE CREATED BLOGS
    // ============================================================

    function handleCreatedBlogs(
        result
    ) {

        if (
            !result ||
            typeof result !== "object"
        ) {
            return;
        }


        const createdBlogIds =
            Array.isArray(
                result.created_blog_ids
            )
                ? result.created_blog_ids
                : [];


        const existingBlogIds =
            Array.isArray(
                result.existing_blog_ids
            )
                ? result.existing_blog_ids
                : [];


        const dbImported =
            result.db_imported === true;


        const dbImporting =
            result.db_importing === true;


        const importError =
            result.import_error ||
            "";


        if (
            dbImporting
        ) {

            return;
        }


        if (
            importError
        ) {

            console.error(
                "QEVRIXA BLOG IMPORT ERROR:",
                importError
            );


            appendCustomInfo(
                "The chatbot response was received, " +
                "but the blog could not be added " +
                "to the Blog Posts list."
            );


            return;
        }


        if (
            createdBlogIds.length > 0
        ) {

            appendCustomInfo(
                createdBlogIds.length +
                (
                    createdBlogIds.length === 1
                        ? " new blog post was added as a draft. "
                        : " new blog posts were added as drafts. "
                ) +
                "Please review and publish them from Blog Posts."
            );


            scrollChatToBottom();


            return;
        }


        if (
            dbImported &&
            existingBlogIds.length > 0
        ) {

            appendCustomInfo(
                "The blog posts are already " +
                "available in the Blog Posts list. " +
                "No duplicate records were created."
            );


            scrollChatToBottom();
        }
    }


    // ============================================================
    // INFORMATION MESSAGE
    // ============================================================

    function appendCustomInfo(
        message
    ) {

        if (!chatBody) {
            return;
        }


        chatBody.innerHTML += `
            <div class="blog-chat-info-message">
                <div class="blog-chat-info-content">
                    ${escapeHtml(message)}
                </div>
            </div>
        `;


        scrollChatToBottom();
    }


    // ============================================================
    // CREATE CHAT JOB
    // ============================================================

    async function createChatJob(
        question
    ) {

        const payload = {

            jsonrpc:
                "2.0",

            method:
                "call",

            params: {
                question:
                    question
            },

            id:
                Date.now()
        };


        const response =
            await fetch(
                CREATE_JOB_URL,
                {
                    method:
                        "POST",

                    headers: {
                        "Content-Type":
                            "application/json",

                        "Accept":
                            "application/json",

                        "X-Requested-With":
                            "XMLHttpRequest"
                    },

                    credentials:
                        "same-origin",

                    body:
                        JSON.stringify(
                            payload
                        )
                }
            );


        const rawText =
            await response.text();


        if (!response.ok) {

            throw new Error(
                "Odoo returned HTTP " +
                response.status
            );
        }


        let data;


        try {

            data =
                JSON.parse(
                    rawText
                );

        } catch (error) {

            throw new Error(
                "Odoo returned invalid JSON."
            );
        }


        if (data.error) {

            throw new Error(
                extractErrorMessage(
                    data.error
                )
            );
        }


        return (
            data.result !== undefined
                ? data.result
                : data
        );
    }


    // ============================================================
    // GET JOB ID
    // ============================================================

    function getJobId(
        result
    ) {

        if (!result) {
            return null;
        }


        if (
            typeof result === "string"
        ) {

            return result;
        }


        if (result.job_id) {
            return result.job_id;
        }


        if (result.id) {
            return result.id;
        }


        if (
            result.data &&
            result.data.job_id
        ) {

            return result.data.job_id;
        }


        if (
            result.result &&
            result.result.job_id
        ) {

            return result.result.job_id;
        }


        return null;
    }


    // ============================================================
    // WAIT FOR CHAT RESULT
    // ============================================================

    async function waitForChatResult(
        jobId,
        loadingId
    ) {

        const startTime =
            Date.now();


        while (
            Date.now() -
            startTime <
            MAX_WAIT_TIME
        ) {

            await sleep(
                STATUS_INTERVAL
            );


            try {

                const rawResult =
                    await checkChatStatus(
                        jobId
                    );


                const result =
                    normalizeStatusResponse(
                        rawResult
                    );


                updateLoadingMessage(
                    loadingId,
                    result
                );


                if (
                    isErrorStatus(
                        result
                    )
                ) {

                    return result;
                }


                if (
                    isProcessingStatus(
                        result
                    )
                ) {

                    continue;
                }


                if (
                    hasActualResponse(
                        result
                    )
                ) {

                    return result;
                }


                if (
                    isCompletedStatus(
                        result
                    )
                ) {

                    return result;
                }


            } catch (error) {

                console.error(
                    "STATUS CHECK ERROR:",
                    error
                );
            }
        }


        throw new Error(
            "The AI service took too long to respond."
        );
    }


    // ============================================================
    // CHECK STATUS
    // ============================================================

    async function checkChatStatus(
        jobId
    ) {

        const payload = {

            jsonrpc:
                "2.0",

            method:
                "call",

            params: {
                job_id:
                    jobId
            },

            id:
                Date.now()
        };


        const response =
            await fetch(
                STATUS_URL,
                {
                    method:
                        "POST",

                    headers: {
                        "Content-Type":
                            "application/json",

                        "Accept":
                            "application/json",

                        "X-Requested-With":
                            "XMLHttpRequest"
                    },

                    credentials:
                        "same-origin",

                    body:
                        JSON.stringify(
                            payload
                        )
                }
            );


        if (!response.ok) {

            throw new Error(
                "Status request failed: HTTP " +
                response.status
            );
        }


        const rawText =
            await response.text();


        let data;


        try {

            data =
                JSON.parse(
                    rawText
                );

        } catch (error) {

            throw new Error(
                "Status endpoint returned invalid JSON."
            );
        }


        if (data.error) {

            throw new Error(
                extractErrorMessage(
                    data.error
                )
            );
        }


        return (
            data.result !== undefined
                ? data.result
                : data
        );
    }


    // ============================================================
    // NORMALIZE STATUS RESPONSE
    // ============================================================

    function normalizeStatusResponse(
        data
    ) {

        if (
            data === null ||
            data === undefined
        ) {

            return {
                status:
                    "processing",
                answer:
                    ""
            };
        }


        if (
            typeof data === "string"
        ) {

            const text =
                data.trim();


            if (!text) {

                return {
                    status:
                        "processing",
                    answer:
                        ""
                };
            }


            try {

                return normalizeStatusResponse(
                    JSON.parse(text)
                );

            } catch (error) {

                return {
                    status:
                        "done",
                    answer:
                        text
                };
            }
        }


        if (
            Array.isArray(data)
        ) {

            return {
                status:
                    "done",
                blogs:
                    data
            };
        }


        if (
            typeof data === "object"
        ) {

            if (
                data.result !== undefined
            ) {

                return normalizeStatusResponse(
                    data.result
                );
            }


            if (
                data.data !== undefined &&
                !data.status
            ) {

                const nested =
                    normalizeStatusResponse(
                        data.data
                    );


                return {
                    ...data,
                    ...nested
                };
            }


            return data;
        }


        return data;
    }


    // ============================================================
    // STATUS HELPERS
    // ============================================================

    function isProcessingStatus(
        result
    ) {

        if (!result) {
            return true;
        }


        const status =
            String(
                result.status ||
                result.state ||
                ""
            ).toLowerCase();


        return (
            status === "processing" ||
            status === "pending" ||
            status === "queued" ||
            status === "running" ||
            status === "started" ||
            status === "waiting"
        );
    }


    function isCompletedStatus(
        result
    ) {

        if (!result) {
            return false;
        }


        const status =
            String(
                result.status ||
                result.state ||
                ""
            ).toLowerCase();


        return (
            status === "done" ||
            status === "completed" ||
            status === "success" ||
            status === "finished"
        );
    }


    function isErrorStatus(
        result
    ) {

        if (!result) {
            return false;
        }


        const status =
            String(
                result.status ||
                result.state ||
                ""
            ).toLowerCase();


        return (
            status === "error" ||
            status === "failed" ||
            status === "failure"
        );
    }


    // ============================================================
    // ACTUAL RESPONSE DETECTION
    // ============================================================

    function hasActualResponse(
        result
    ) {

        if (
            result === null ||
            result === undefined
        ) {

            return false;
        }


        if (
            Array.isArray(result)
        ) {

            return result.length > 0;
        }


        if (
            typeof result === "string"
        ) {

            return result.trim().length > 0;
        }


        if (
            typeof result === "object"
        ) {

            const textFields = [
                "answer",
                "response",
                "content",
                "message",
                "text"
            ];


            for (
                let i = 0;
                i < textFields.length;
                i++
            ) {

                const value =
                    result[
                        textFields[i]
                    ];


                if (
                    typeof value === "string" &&
                    value.trim()
                ) {

                    return true;
                }
            }


            if (
                Array.isArray(
                    result.blogs
                ) &&
                result.blogs.length > 0
            ) {

                return true;
            }


            if (
                Array.isArray(
                    result.data
                ) &&
                result.data.length > 0
            ) {

                return true;
            }


            if (
                Array.isArray(
                    result.result
                ) &&
                result.result.length > 0
            ) {

                return true;
            }
        }


        return false;
    }


    // ============================================================
    // UPDATE LOADING
    // ============================================================

    function updateLoadingMessage(
        loadingId,
        result
    ) {

        const element =
            document.getElementById(
                loadingId
            );


        if (!element) {
            return;
        }


        let text =
            "Thinking...";


        if (
            isProcessingStatus(
                result
            )
        ) {

            text =
                "Searching blog posts...";
        }


        if (
            result &&
            result.status === "running"
        ) {

            text =
                "Generating answer...";
        }


        if (
            isCompletedStatus(
                result
            )
        ) {

            text =
                "Preparing response...";
        }


        const textElement =
            element.querySelector(
                ".blog-chat-loading-text"
            );


        if (textElement) {

            textElement.textContent =
                text;
        }
    }


    // ============================================================
    // USER MESSAGE
    // ============================================================

    function appendUserMessage(
        question
    ) {

        if (!chatBody) {
            return;
        }


        chatBody.innerHTML += `
            <div class="blog-chat-user-message">
                <div class="blog-chat-message-content">
                    ${escapeHtml(question)}
                </div>
            </div>
        `;


        scrollChatToBottom();
    }


    // ============================================================
    // BOT MESSAGE
    // ============================================================

    function appendBotMessage(
        reply
    ) {

        if (!chatBody) {
            return;
        }


        chatBody.innerHTML += `
            <div class="blog-chat-bot-message">
                <div class="blog-chat-message-content">
                    ${reply}
                </div>
            </div>
        `;


        scrollChatToBottom();
    }


    // ============================================================
    // LOADING
    // ============================================================

    function appendLoadingMessage(
        loadingId
    ) {

        if (!chatBody) {
            return;
        }


        chatBody.innerHTML += `
            <div
                id="${loadingId}"
                class="blog-chat-loading"
            >
                <div class="blog-chat-loading-content">
                    <span class="blog-chat-loading-text">
                        Thinking...
                    </span>
                </div>
            </div>
        `;


        scrollChatToBottom();
    }


    // ============================================================
    // REMOVE LOADING
    // ============================================================

    function removeLoadingMessage(
        loadingId
    ) {

        const element =
            document.getElementById(
                loadingId
            );


        if (element) {
            element.remove();
        }
    }


    // ============================================================
    // ERROR
    // ============================================================

    function appendCustomError(
        message
    ) {

        if (!chatBody) {
            return;
        }


        chatBody.innerHTML += `
            <div class="blog-chat-error-message">
                <div class="blog-chat-error-content">
                    <strong>
                        AI Chat Error
                    </strong>

                    <br>

                    <small>
                        ${escapeHtml(message)}
                    </small>
                </div>
            </div>
        `;


        scrollChatToBottom();
    }


    // ============================================================
    // SCROLL
    // ============================================================

    function scrollChatToBottom() {

        if (chatBody) {

            chatBody.scrollTop =
                chatBody.scrollHeight;
        }
    }


    // ============================================================
    // EXTRACT REPLY
    // ============================================================

    function extractReply(
        data
    ) {

        if (
            data === null ||
            data === undefined
        ) {

            return "";
        }


        if (
            typeof data === "string"
        ) {

            return parseAnswer(
                data
            );
        }


        if (
            Array.isArray(data)
        ) {

            return formatArrayResponse(
                data
            );
        }


        if (
            typeof data === "object"
        ) {

            if (data.error) {

                return `
                    <strong class="blog-chat-inline-error">
                        ${escapeHtml(
                            extractErrorMessage(
                                data.error
                            )
                        )}
                    </strong>
                `;
            }


            if (
                Array.isArray(
                    data.blogs
                )
            ) {

                return formatArrayResponse(
                    data.blogs
                );
            }


            if (
                Array.isArray(
                    data.data
                )
            ) {

                return formatArrayResponse(
                    data.data
                );
            }


            const textFields = [
                "answer",
                "response",
                "content",
                "message",
                "text"
            ];


            for (
                let i = 0;
                i < textFields.length;
                i++
            ) {

                const value =
                    data[
                        textFields[i]
                    ];


                if (
                    typeof value === "string" &&
                    value.trim()
                ) {

                    return parseAnswer(
                        value
                    );
                }
            }


            if (
                data.result !== undefined &&
                data.result !== null
            ) {

                return extractReply(
                    data.result
                );
            }


            if (
                data.data !== undefined &&
                data.data !== null
            ) {

                return extractReply(
                    data.data
                );
            }


            if (
                Array.isArray(
                    data.messages
                )
            ) {

                return formatMessages(
                    data.messages
                );
            }


            try {

                return `
                    <pre class="blog-chat-raw-response">
                        ${escapeHtml(
                            JSON.stringify(
                                data,
                                null,
                                2
                            )
                        )}
                    </pre>
                `;

            } catch (error) {

                return "";
            }
        }


        return escapeHtml(
            String(data)
        );
    }


    // ============================================================
    // PARSE ANSWER
    // ============================================================

    function parseAnswer(
        answer
    ) {

        if (
            answer === null ||
            answer === undefined
        ) {

            return "";
        }


        if (
            typeof answer === "object"
        ) {

            return extractReply(
                answer
            );
        }


        const text =
            String(
                answer
            ).trim();


        if (!text) {
            return "";
        }


        if (
            (
                text.startsWith("[") &&
                text.endsWith("]")
            ) ||
            (
                text.startsWith("{") &&
                text.endsWith("}")
            )
        ) {

            try {

                return extractReply(
                    JSON.parse(text)
                );

            } catch (error) {
                // Continue as plain text.
            }
        }


        return formatText(
            text
        );
    }


    // ============================================================
    // FORMAT TEXT
    // ============================================================

    function formatText(
        text
    ) {

        return escapeHtml(
            String(text)
        ).replace(
            /\n/g,
            "<br>"
        );
    }


    // ============================================================
    // FORMAT BLOG ARRAY
    // ============================================================

    function formatArrayResponse(
        items
    ) {

        if (
            !Array.isArray(items) ||
            !items.length
        ) {

            return "No blog posts were found.";
        }


        let html =
            "";


        items.forEach(
            function (blog) {

                if (
                    !blog ||
                    typeof blog !== "object"
                ) {

                    return;
                }


                const title =
                    blog.title ||
                    blog.name ||
                    "Untitled Blog";


                const introduction =
                    blog.introduction ||
                    blog.description ||
                    blog.short_description ||
                    "";


                const publishDate =
                    blog.published_on ||
                    blog.publish_date ||
                    blog.published_date ||
                    "";


                const author =
                    blog.author ||
                    "";


                const category =
                    blog.category ||
                    "";


                let url =
                    blog.url ||
                    "";


                const image =
                    cleanUrl(
                        blog.image
                    );


                if (
                    !url &&
                    blog.slug
                ) {

                    url =
                        "/blog/" +
                        encodeURIComponent(
                            String(
                                blog.slug
                            )
                        );
                }


                url =
                    cleanUrl(
                        url
                    );


                html += `
                    <div class="blog-chat-result">
                `;


                if (
                    isSafeUrl(image)
                ) {

                    html += `
                        <div class="blog-chat-result-image">
                            <img
                                src="${escapeHtml(image)}"
                                alt="${escapeHtml(
                                    String(title)
                                )}"
                                loading="lazy"
                                onerror="
                                    this.style.display='none';
                                "
                            />
                        </div>
                    `;
                }


                html += `
                    <h3 class="blog-chat-result-title">
                        ${escapeHtml(
                            String(title)
                        )}
                    </h3>
                `;


                if (publishDate) {

                    html += `
                        <div class="blog-chat-result-meta">
                            📅 ${escapeHtml(
                                String(publishDate)
                            )}
                        </div>
                    `;
                }


                if (author) {

                    html += `
                        <div class="blog-chat-result-meta">
                            ✍️ ${escapeHtml(
                                String(author)
                            )}
                        </div>
                    `;
                }


                if (category) {

                    html += `
                        <div class="blog-chat-result-meta">
                            📂 ${escapeHtml(
                                String(category)
                            )}
                        </div>
                    `;
                }


                if (introduction) {

                    html += `
                        <p class="blog-chat-result-description">
                            ${escapeHtml(
                                String(introduction)
                            )}
                        </p>
                    `;
                }


                if (
                    isSafeUrl(url)
                ) {

                    html += `
                        <a
                            href="${escapeHtml(url)}"
                            target="_blank"
                            rel="noopener noreferrer"
                            class="blog-chat-result-link"
                        >
                            🔗 Read Blog
                        </a>
                    `;
                }


                if (
                    Array.isArray(
                        blog.sections
                    )
                ) {

                    blog.sections.forEach(
                        function (section) {

                            if (
                                !section ||
                                typeof section !== "object"
                            ) {

                                return;
                            }


                            html += `
                                <div class="blog-chat-section">
                                    <h4>
                                        ${escapeHtml(
                                            String(
                                                section.title ||
                                                ""
                                            )
                                        )}
                                    </h4>

                                    <p>
                                        ${escapeHtml(
                                            String(
                                                section.content ||
                                                ""
                                            )
                                        )}
                                    </p>
                                </div>
                            `;
                        }
                    );
                }


                if (
                    Array.isArray(
                        blog.key_takeaways
                    ) &&
                    blog.key_takeaways.length
                ) {

                    html += `
                        <div class="blog-chat-list-section">
                            <strong>
                                Key Takeaways
                            </strong>

                            <ul>
                    `;


                    blog.key_takeaways.forEach(
                        function (item) {

                            html += `
                                <li>
                                    ${escapeHtml(
                                        String(item)
                                    )}
                                </li>
                            `;
                        }
                    );


                    html += `
                            </ul>
                        </div>
                    `;
                }


                if (
                    Array.isArray(
                        blog.follow_up_questions
                    ) &&
                    blog.follow_up_questions.length
                ) {

                    html += `
                        <div class="blog-chat-list-section">
                            <strong>
                                You can also ask:
                            </strong>

                            <ul>
                    `;


                    blog.follow_up_questions.forEach(
                        function (question) {

                            html += `
                                <li>
                                    ${escapeHtml(
                                        String(question)
                                    )}
                                </li>
                            `;
                        }
                    );


                    html += `
                            </ul>
                        </div>
                    `;
                }


                if (
                    Array.isArray(
                        blog.references
                    ) &&
                    blog.references.length
                ) {

                    html += `
                        <div class="blog-chat-references">
                            <strong>
                                References
                            </strong>

                            <ul>
                    `;


                    blog.references.forEach(
                        function (reference) {

                            if (
                                !reference ||
                                typeof reference !== "object"
                            ) {

                                return;
                            }


                            const refUrl =
                                cleanUrl(
                                    reference.url
                                );


                            if (
                                isSafeUrl(refUrl)
                            ) {

                                html += `
                                    <li>
                                        <a
                                            href="${escapeHtml(
                                                refUrl
                                            )}"
                                            target="_blank"
                                            rel="noopener noreferrer"
                                        >
                                            ${escapeHtml(
                                                String(
                                                    reference.title ||
                                                    "Reference"
                                                )
                                            )}
                                        </a>
                                    </li>
                                `;
                            }
                        }
                    );


                    html += `
                            </ul>
                        </div>
                    `;
                }


                html += `
                    </div>
                `;
            }
        );


        return html;
    }


    // ============================================================
    // FORMAT MESSAGES
    // ============================================================

    function formatMessages(
        messages
    ) {

        if (
            !messages ||
            !messages.length
        ) {

            return "";
        }


        for (
            let i =
                messages.length - 1;
            i >= 0;
            i--
        ) {

            const message =
                messages[i];


            if (!message) {
                continue;
            }


            if (message.content) {

                return extractReply(
                    message.content
                );
            }


            if (message.message) {

                return parseAnswer(
                    message.message
                );
            }
        }


        return "";
    }


    // ============================================================
    // CLEAN URL
    // ============================================================

    function cleanUrl(
        value
    ) {

        if (!value) {
            return "";
        }


        let url =
            String(
                value
            ).trim();


        const markdownMatch =
            url.match(
                /^\[.*?\]\((.*?)\)$/
            );


        if (
            markdownMatch &&
            markdownMatch[1]
        ) {

            url =
                markdownMatch[1];
        }


        return url.trim();
    }


    // ============================================================
    // SAFE URL
    // ============================================================

    function isSafeUrl(
        url
    ) {

        if (!url) {
            return false;
        }


        const value =
            cleanUrl(
                url
            );


        if (
            value.startsWith("/") ||
            value.startsWith("#")
        ) {

            return true;
        }


        try {

            const parsed =
                new URL(
                    value,
                    window.location.origin
                );


            return (
                parsed.protocol === "http:" ||
                parsed.protocol === "https:"
            );

        } catch (error) {

            return false;
        }
    }


    // ============================================================
    // GET ERROR MESSAGE
    // ============================================================

    function getErrorMessage(
        result
    ) {

        if (!result) {

            return "Unknown chatbot error.";
        }


        if (
            typeof result === "string"
        ) {

            return result;
        }


        if (
            result.answer &&
            String(
                result.answer
            ).trim()
        ) {

            return String(
                result.answer
            );
        }


        if (result.error) {

            return extractErrorMessage(
                result.error
            );
        }


        if (result.message) {

            return String(
                result.message
            );
        }


        if (result.response) {

            return String(
                result.response
            );
        }


        return (
            "The chatbot encountered " +
            "an unexpected error."
        );
    }


    // ============================================================
    // EXTRACT ERROR
    // ============================================================

    function extractErrorMessage(
        error
    ) {

        if (!error) {

            return "Unknown chatbot error.";
        }


        if (
            typeof error === "string"
        ) {

            return error;
        }


        if (
            error.data &&
            error.data.message
        ) {

            return String(
                error.data.message
            );
        }


        if (error.message) {

            return String(
                error.message
            );
        }


        if (error.name) {

            return String(
                error.name
            );
        }


        try {

            return JSON.stringify(
                error
            );

        } catch (exception) {

            return String(
                error
            );
        }
    }


    // ============================================================
    // ESCAPE HTML
    // ============================================================

    function escapeHtml(
        value
    ) {

        return String(value)
            .replace(
                /&/g,
                "&amp;"
            )
            .replace(
                /</g,
                "&lt;"
            )
            .replace(
                />/g,
                "&gt;"
            )
            .replace(
                /"/g,
                "&quot;"
            )
            .replace(
                /'/g,
                "&#039;"
            );
    }


    // ============================================================
    // SLEEP
    // ============================================================

    function sleep(
        milliseconds
    ) {

        return new Promise(
            function (resolve) {

                setTimeout(
                    resolve,
                    milliseconds
                );
            }
        );
    }


    // ============================================================
    // PUBLIC ADMIN INITIALIZER
    // ============================================================

    window.qevrixaInitBlogChat =
        function () {

            console.log(
                "QEVRIXA BLOG CHAT: " +
                "Admin initializer called."
            );


            /*
             * The admin component has already been created by
             * blog_admin_chat.js. We only need the backend check
             * and the DOM references here.
             */

            if (
                !isOdooBackendPage()
            ) {

                console.log(
                    "QEVRIXA BLOG CHAT: " +
                    "Not Odoo backend."
                );

                return;
            }


            initBlogChat();
        };


    // ============================================================
    // ROUTING PROTECTION
    // ============================================================

    setInterval(
        function () {

            const currentPath =
                getCurrentPath();


            if (
                currentPath !==
                lastPath
            ) {

                lastPath =
                    currentPath;


                console.log(
                    "QEVRIXA BLOG CHAT: " +
                    "Route changed to:",
                    currentPath
                );


                /*
                 * Only initialize when the Admin OWL component
                 * actually exists.
                 */

                setTimeout(
                    function () {

                        const adminRoot =
                            getAdminChatRoot();


                        if (
                            adminRoot
                        ) {

                            initBlogChat();

                        } else {

                            clearChatReferences();
                        }

                    },
                    500
                );
            }

        },
        500
    );


    // ============================================================
    // INITIAL DOM CHECK
    // ============================================================

    if (
        document.readyState ===
        "loading"
    ) {

        document.addEventListener(
            "DOMContentLoaded",
            function () {

                setTimeout(
                    function () {

                        const adminRoot =
                            getAdminChatRoot();


                        if (
                            adminRoot
                        ) {

                            window.qevrixaInitBlogChat();
                        }

                    },
                    300
                );

            },
            {
                once: true
            }
        );

    } else {

        setTimeout(
            function () {

                const adminRoot =
                    getAdminChatRoot();


                if (
                    adminRoot
                ) {

                    window.qevrixaInitBlogChat();
                }

            },
            500
        );
    }


    // ============================================================
    // FINAL LOG
    // ============================================================

    console.log(
        "QEVRIXA BLOG CHAT: " +
        "ADMIN CHAT SCRIPT READY"
    );

}());

