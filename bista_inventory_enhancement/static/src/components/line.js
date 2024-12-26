/** @odoo-module **/

import LineComponent from '@stock_barcode/components/line';
import { patch } from 'web.utils'

patch(LineComponent.prototype, "stock_inventory_line_component", {

    setup() {
        // Initialize with the initial value of qtyDone
        this.initialQtyDone = this.qtyDone;
    },
    
    get isSameLocation() {
        if (this.env.model.params.model === 'stock.inventory') {
            return false;
        }
        return this.env.model.location.id === this.line.location_id;
    },

    get isblind() {
        if (this.env.model.lineModel === 'stock.inventory.line' && this.env.model.record.blind_count === false) {
            return true;
        } else {
            return false;
        }
    },


});
