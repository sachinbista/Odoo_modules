/** @odoo-module **/

import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";
import { CharField } from "@web/views/fields/char/char_field";
import { useInputField } from "@web/views/fields/input_field_hook";
import { Dialog } from "@web/core/dialog/dialog";
const { useRef, Component, onMounted,onWillStart } = owl;
import { useService } from "@web/core/utils/hooks";
import { qweb } from 'web.core';
import { debounce } from"@web/core/utils/timing";
import { markup, toRaw } from "@odoo/owl";

class BatchPopover extends Component {
    async setup() {
        this.orm = useService("orm");
        onWillStart(async () => {
            if(this.props.record.batch_id){
                this.props.pickings = await this.orm.call('stock.picking','search_read',[],{fields: ["id", "name","origin","partner_id"],
                    'domain':[['batch_id','=',this.props.record.batch_id[0]]]
                });
            }
        });
        super.setup();
    }
}

BatchPopover.template = "BatchPopover";

export class KanbanPopup extends Component {

    /**
    * The purpose of this extension
    * is to allow initialize component
    * @override
    */
    setup() {
        super.setup();
        this.popover = useService("popover");
        this.orm = useService("orm");
    }
    onClickPopupIcon(ev){
        ev.preventDefault();
        ev.stopPropagation();
        ev.stopImmediatePropagation();
        var self = this;
        self.popover.add(ev.currentTarget,self.constructor.components.Popover,{
        'record': self.props.record.data},
        {closeOnClickAway: true}
        );
    }
}

KanbanPopup.template = "KanbanPopUp";
KanbanPopup.components = {
    Popover: BatchPopover,
}
registry.category("fields").add("KanbanPopup", KanbanPopup);
