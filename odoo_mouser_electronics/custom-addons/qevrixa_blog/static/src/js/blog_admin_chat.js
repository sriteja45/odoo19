/** @odoo-module **/

import {
    Component,
    onMounted,
    onWillUnmount,
} from "@odoo/owl";

import {
    registry,
} from "@web/core/registry";

console.log(
    "QEVRIXA ADMIN BLOG CHAT JS LOADED"
);


// =============================================================
// BLOG ADMIN CHAT COMPONENT
// =============================================================

export class BlogAdminChat extends Component {

    static template =
        "qevrixa_blog.BlogAdminChat";


    setup() {

        this.routeTimer =
            null;

        this.initializationTimer =
            null;

        this.lastPath =
            window.location.pathname || "";

        this.chatLogicRetryTimer =
            null;


        // =========================================================
        // COMPONENT MOUNTED
        // =========================================================

        onMounted(
            () => {

                console.log(
                    "QEVRIXA ADMIN BLOG CHAT: " +
                    "COMPONENT MOUNTED"
                );

                this.startChatWatcher();

            }
        );


        // =========================================================
        // COMPONENT UNMOUNTED
        // =========================================================

        onWillUnmount(
            () => {

                console.log(
                    "QEVRIXA ADMIN BLOG CHAT: " +
                    "COMPONENT UNMOUNTED"
                );

                this.clearTimers();

            }
        );
    }


    // =============================================================
    // CLEAR TIMERS
    // =============================================================

    clearTimers() {

        if (
            this.routeTimer
        ) {

            clearInterval(
                this.routeTimer
            );

            this.routeTimer =
                null;
        }


        if (
            this.initializationTimer
        ) {

            clearInterval(
                this.initializationTimer
            );

            this.initializationTimer =
                null;
        }


        if (
            this.chatLogicRetryTimer
        ) {

            clearInterval(
                this.chatLogicRetryTimer
            );

            this.chatLogicRetryTimer =
                null;
        }
    }


    // =============================================================
    // START CHAT WATCHER
    // =============================================================

    startChatWatcher() {

        console.log(
            "QEVRIXA ADMIN BLOG CHAT: " +
            "STARTING CHAT WATCHER"
        );


        this.checkAndInitialize();


        this.routeTimer =
            setInterval(
                () => {

                    const currentPath =
                        window.location.pathname || "";


                    if (
                        currentPath !==
                        this.lastPath
                    ) {

                        console.log(
                            "QEVRIXA ADMIN BLOG CHAT: " +
                            "ROUTE CHANGED"
                        );

                        console.log(
                            "OLD PATH:",
                            this.lastPath
                        );

                        console.log(
                            "NEW PATH:",
                            currentPath
                        );

                        this.lastPath =
                            currentPath;


                        setTimeout(
                            () => {

                                this.checkAndInitialize();

                            },
                            700
                        );
                    }

                },
                500
            );
    }


    // =============================================================
    // BLOG ADMIN PAGE CHECK
    // =============================================================

    isBlogAdminPage() {

        const currentPath =
            window.location.pathname || "";


        const isOdooBackend =
            currentPath.startsWith(
                "/odoo"
            );


        if (
            !isOdooBackend
        ) {

            return false;
        }


        // ---------------------------------------------------------
        // PAGE TEXT
        // ---------------------------------------------------------

        const bodyText =
            document.body &&
            document.body.innerText
                ? document.body.innerText.toLowerCase()
                : "";


        const hasBlogPostsText =
            bodyText.includes(
                "blog posts"
            );


        // ---------------------------------------------------------
        // ODOO LIST
        // ---------------------------------------------------------

        const hasOdooList =
            !!document.querySelector(
                ".o_list_view, " +
                ".o_list_renderer, " +
                ".o_list_table"
            );


        // ---------------------------------------------------------
        // BLOG HEADING / BREADCRUMB
        // ---------------------------------------------------------

        const hasBlogHeading =
            !!Array.from(
                document.querySelectorAll(
                    "h1, h2, h3, " +
                    ".o_breadcrumb, " +
                    ".o_control_panel"
                )
            ).find(
                (element) => {

                    const text =
                        String(
                            element.innerText ||
                            ""
                        ).toLowerCase();

                    return (
                        text.includes(
                            "blog posts"
                        ) ||
                        text.includes(
                            "qevrixa blog"
                        )
                    );
                }
            );


        // ---------------------------------------------------------
        // ADD BUTTON
        // ---------------------------------------------------------

        const hasNewButton =
            !!document.querySelector(
                ".o_list_button_add"
            );


        const result =
            isOdooBackend &&
            (
                hasBlogPostsText ||
                hasBlogHeading
            ) &&
            (
                hasOdooList ||
                hasNewButton
            );


        console.log(
            "QEVRIXA ADMIN BLOG CHAT: PAGE CHECK",
            {
                isOdooBackend,
                hasBlogPostsText,
                hasBlogHeading,
                hasOdooList,
                hasNewButton,
                result,
            }
        );


        return result;
    }


    // =============================================================
    // CHECK AND INITIALIZE
    // =============================================================

    checkAndInitialize() {

        const isBlogPage =
            this.isBlogAdminPage();


        console.log(
            "QEVRIXA ADMIN BLOG CHAT: " +
            "BLOG PAGE CHECK =",
            isBlogPage
        );


        if (
            !isBlogPage
        ) {

            this.hideChat();

            return;
        }


        this.showChat();

        this.waitForChatElements();
    }


    // =============================================================
    // SHOW CHAT
    // =============================================================

    showChat() {

        if (
            !this.el
        ) {
            return;
        }


        this.el.style.display =
            "";
    }


    // =============================================================
    // HIDE CHAT
    // =============================================================

    hideChat() {

        if (
            !this.el
        ) {
            return;
        }


        console.log(
            "QEVRIXA ADMIN BLOG CHAT: " +
            "HIDING CHAT"
        );


        this.el.style.display =
            "none";
    }


    // =============================================================
    // FIND CHAT ELEMENTS
    //
    // IMPORTANT:
    // Search INSIDE this.el only.
    //
    // This prevents the admin chatbot from accidentally using
    // the public chatbot elements.
    // =============================================================

    getChatElements() {

        if (
            !this.el
        ) {

            return {
                chatButton:
                    null,

                chatWindow:
                    null,

                closeButton:
                    null,

                questionInput:
                    null,

                sendButton:
                    null,

                chatBody:
                    null,
            };
        }


        return {

            chatButton:
                this.el.querySelector(
                    "#blog-chat-button, " +
                    ".qevrixa-blog-chat-button"
                ),

            chatWindow:
                this.el.querySelector(
                    "#blog-chat-window, " +
                    ".qevrixa-blog-chat-window"
                ),

            closeButton:
                this.el.querySelector(
                    "#close-blog-chat, " +
                    ".qevrixa-blog-chat-close"
                ),

            questionInput:
                this.el.querySelector(
                    "#blog-question"
                ),

            sendButton:
                this.el.querySelector(
                    "#send-blog-question"
                ),

            chatBody:
                this.el.querySelector(
                    "#blog-chat-body, " +
                    ".qevrixa-blog-chat-body"
                ),
        };
    }


    // =============================================================
    // WAIT FOR CHAT ELEMENTS
    // =============================================================

    waitForChatElements() {

        if (
            this.initializationTimer
        ) {

            clearInterval(
                this.initializationTimer
            );

            this.initializationTimer =
                null;
        }


        let attempts =
            0;


        const maxAttempts =
            30;


        console.log(
            "QEVRIXA ADMIN BLOG CHAT: " +
            "WAITING FOR CHAT ELEMENTS"
        );


        this.initializationTimer =
            setInterval(
                () => {

                    attempts++;


                    if (
                        !this.isBlogAdminPage()
                    ) {

                        clearInterval(
                            this.initializationTimer
                        );

                        this.initializationTimer =
                            null;

                        return;
                    }


                    const elements =
                        this.getChatElements();


                    console.log(
                        "QEVRIXA ADMIN BLOG CHAT: ELEMENTS",
                        {
                            button:
                                !!elements.chatButton,

                            window:
                                !!elements.chatWindow,

                            close:
                                !!elements.closeButton,

                            input:
                                !!elements.questionInput,

                            send:
                                !!elements.sendButton,

                            body:
                                !!elements.chatBody,
                        }
                    );


                    if (
                        elements.chatButton &&
                        elements.chatWindow &&
                        elements.questionInput &&
                        elements.chatBody
                    ) {

                        console.log(
                            "QEVRIXA ADMIN BLOG CHAT: " +
                            "CHAT ELEMENTS FOUND"
                        );


                        clearInterval(
                            this.initializationTimer
                        );

                        this.initializationTimer =
                            null;


                        this.startExistingChatLogic();

                        return;
                    }


                    if (
                        attempts >=
                        maxAttempts
                    ) {

                        clearInterval(
                            this.initializationTimer
                        );

                        this.initializationTimer =
                            null;


                        console.error(
                            "QEVRIXA ADMIN BLOG CHAT: " +
                            "CHAT ELEMENTS NOT FOUND"
                        );
                    }

                },
                500
            );
    }


    // =============================================================
    // START EXISTING CHAT LOGIC
    // =============================================================

    startExistingChatLogic() {

        console.log(
            "QEVRIXA ADMIN BLOG CHAT: " +
            "STARTING CHAT LOGIC"
        );


        if (
            typeof window.qevrixaInitBlogChat ===
            "function"
        ) {

            try {

                window.qevrixaInitBlogChat();

                console.log(
                    "QEVRIXA ADMIN BLOG CHAT: " +
                    "CHAT LOGIC STARTED SUCCESSFULLY"
                );

            } catch (error) {

                console.error(
                    "QEVRIXA ADMIN BLOG CHAT: " +
                    "ERROR STARTING CHAT LOGIC:",
                    error
                );
            }

            return;
        }


        // ---------------------------------------------------------
        // CHAT JS MAY LOAD AFTER OWL COMPONENT
        // ---------------------------------------------------------

        console.warn(
            "QEVRIXA ADMIN BLOG CHAT: " +
            "qevrixaInitBlogChat NOT AVAILABLE YET"
        );


        if (
            this.chatLogicRetryTimer
        ) {

            clearInterval(
                this.chatLogicRetryTimer
            );
        }


        let retryCount =
            0;


        this.chatLogicRetryTimer =
            setInterval(
                () => {

                    retryCount++;


                    if (
                        typeof window.qevrixaInitBlogChat ===
                        "function"
                    ) {

                        clearInterval(
                            this.chatLogicRetryTimer
                        );

                        this.chatLogicRetryTimer =
                            null;


                        console.log(
                            "QEVRIXA ADMIN BLOG CHAT: " +
                            "CHAT LOGIC NOW AVAILABLE"
                        );


                        try {

                            window.qevrixaInitBlogChat();

                        } catch (error) {

                            console.error(
                                "QEVRIXA ADMIN BLOG CHAT: " +
                                "INITIALIZER ERROR:",
                                error
                            );
                        }

                        return;
                    }


                    if (
                        retryCount >=
                        20
                    ) {

                        clearInterval(
                            this.chatLogicRetryTimer
                        );

                        this.chatLogicRetryTimer =
                            null;


                        console.error(
                            "QEVRIXA ADMIN BLOG CHAT: " +
                            "CHAT LOGIC COULD NOT BE LOADED"
                        );
                    }

                },
                500
            );
    }
}


// =============================================================
// REGISTER COMPONENT
// =============================================================

registry
    .category(
        "main_components"
    )
    .add(
        "qevrixa_blog_admin_chat",
        {
            Component:
                BlogAdminChat,
        }
    );


console.log(
    "QEVRIXA ADMIN BLOG CHAT COMPONENT REGISTERED"
);

