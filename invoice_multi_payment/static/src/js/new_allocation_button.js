/** @odoo-module **/

import { ListController } from "@web/views/list/list_controller";
import { listView } from "@web/views/list/list_view";
import { registry } from '@web/core/registry';

export class AllocateButtonsController extends ListController {
    setup() {
        super.setup();
    }
}



registry.category('views').add('invoice_multi_payment', {
    ...listView,
    Controller: AllocateButtonsController,
    buttonTemplate: "AllocateAmount.buttons",

});