/** @odoo-module **/

import { Composer } from "@mail/core/common/composer";
import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";
import { toRaw } from "@odoo/owl";

patch(Composer.prototype, {

    setup() {
        super.setup();

        this.orm = useService("orm");
        this.notification = useService("notification");
    },

    async askAI() {

        try {

            const composer = toRaw(this.props.composer);

            const prompt = composer.composerText || "";

            if (!prompt.trim()) {

                this.notification.add(
                    "Please enter a question.",
                    {
                        type: "warning",
                    }
                );

                return;
            }

            const thread = composer.thread;

            if (!thread) {

                this.notification.add(
                    "Thread not found.",
                    {
                        type: "danger",
                    }
                );

                return;
            }

            await this.orm.call(
                "discuss.channel",
                "generate_ai_reply",
                [
                    thread.id,
                    prompt,
                ]
            );
            composer.composerText = "";

        }
        catch (error) {

            console.error(error);

            this.notification.add(
                "Unable to contact AI.",
                {
                    type: "danger",
                }
            );
        }

    },

});