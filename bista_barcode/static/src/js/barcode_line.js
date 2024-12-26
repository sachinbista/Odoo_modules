/** @odoo-module **/

import {patch} from 'web.utils';
import LineComponent from '@stock_barcode/components/line';

patch(LineComponent.prototype, 'bista_barcode/static/src/js/barcode_line.js', {

    edit() {
        let record = this.env.model.record
        if (record && record.picking_type_id && !record.picking_type_id.allow_edit) {
            return this.env.model.notification.add("Editing line is restricted for this operation type", {
                type: 'danger',
                'sticky': false
            });
        }
        return this._super.apply(this, arguments)
    }

});
