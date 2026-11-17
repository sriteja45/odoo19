/** @odoo-module **/

import { registerComposerAction } from "@mail/core/common/composer_actions";
import { _t } from "@web/core/l10n/translation";

registerComposerAction("xevoria_ai", {

    id: "xevoria_ai",

    name: _t("Ask AI"),

    icon: "fa fa-magic",

    /**
     * Show for every composer.
     */
    condition() {
        return true;
    },

    /**
     * Put before emoji.
     */
    sequenceQuick: 1,

    async onSelected({ owner }) {
        await owner.askAI();
    },
});