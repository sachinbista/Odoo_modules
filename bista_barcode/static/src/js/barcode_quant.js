/** @odoo-module **/

import {patch} from 'web.utils';
import BarcodePickingModel from '@stock_barcode/models/barcode_quant_model';


patch(BarcodePickingModel.prototype, 'bista_barcode/static/src/js/barcode_quant.js', {

    async _processBarcode(barcode) {
        let _super = this._super,
            args = arguments,
            barcodeData = {};

        const self = this
        self.selectedLineVirtualId = false
        self.selectLine(false)

        let res = await _super.apply(this, arguments);
        let lot_ids = await self.orm.searchRead(
            'stock.lot',
            [['name', '=', barcode], ['product_id.tracking', '=', 'lot']],
            ['id', 'product_id', 'product_barcode', 'product_qty'],
            {limit: 1, load: false}
        )
        if (lot_ids.length) {
            let lot = lot_ids[0]
            let scanned_line = self.currentState.lines.filter(function (mvl) {
                return mvl.lot_id && mvl.lot_id.name === barcode
            })
            if (scanned_line.length) {
                let line = scanned_line[0]
                self.selectedLineVirtualId = line.virtual_id
                self.selectLine(line)
                line['inventory_quantity'] = lot.product_qty
                self.trigger("update")

            }
        } else {
            let scanned_line = this.currentState.lines.filter(function (mvl) {
                return mvl.product_id.barcode && mvl.product_id.barcode === barcode
            })
            if (scanned_line.length) {
                let line = scanned_line[0]
                self.selectedLineVirtualId = line.virtual_id
                self.selectLine(line)
                self.trigger("update")
            }
        }
        return res

    },

    doneCycleCount() {
        this.trigger('history-back');
    },

    get displayApplyButton() {
        return this.groups.group_stock_manager
    },

    get displaySubmitButton() {
        return !this.groups.group_stock_manager
    }

});

