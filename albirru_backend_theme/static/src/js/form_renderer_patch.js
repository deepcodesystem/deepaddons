/** @odoo-module **/

import { FormRenderer } from "@web/views/form/form_renderer";
import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";
import { onMounted, onWillUnmount } from "@odoo/owl";

patch(FormRenderer.prototype, {
    setup() {
        super.setup(...arguments);
        this.albirruTheme = useService("albirruTheme");
        
        // Listen for theme changes to re-render if needed
        const onThemeChanged = () => {
            this.render();
            // Trigger resize to force layout re-calculation
            window.dispatchEvent(new Event('resize'));
        };
        onMounted(() => {
            this.albirruTheme.bus.addEventListener('THEME_CHANGED', onThemeChanged);
        });
        onWillUnmount(() => {
            this.albirruTheme.bus.removeEventListener('THEME_CHANGED', onThemeChanged);
        });
    },

    /**
     * Override mailLayout to respect Albirru theme settings
     */
    mailLayout(hasAttachmentContainer) {
        const res = super.mailLayout(...arguments);
        
        // If theme service is not available or settings not loaded, return original
        if (!this.albirruTheme) {
            return res;
        }

        const settings = this.albirruTheme.getSettings();
        
        // If user wants chatter at the bottom, we override "aside" layouts
        if (settings.chatter_position === 'bottom') {
            if (res === "SIDE_CHATTER") {
                return "BOTTOM_CHATTER";
            }
            if (res === "EXTERNAL_COMBO_XXL") {
                return "EXTERNAL_COMBO";
            }
        }
        
        return res;
    },
});
