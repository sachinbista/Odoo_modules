/** @odoo-module  */

import { ButtonBox } from '@web/views/form/button_box/button_box';
import { useService } from "@web/core/utils/hooks";
import { patch } from "@web/core/utils/patch";

patch(ButtonBox.prototype,"button_box",{
    async setup() {
        this._super();
        const ui = useService("ui");
        this.getMaxButtons = () => [2, 2, 2, 4][ui.size] || 5;
    }

});