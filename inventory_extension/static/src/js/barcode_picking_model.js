/** @odoo-module **/

import BarcodePickingModel from '@stock_barcode/models/barcode_picking_model';

import { patch } from "@web/core/utils/patch";
import { _t } from "@web/core/l10n/translation";

patch(BarcodePickingModel.prototype, {
    async validate() {
        // this.validateContext['from_barcode'] = true;
        if (this.resModel == 'stock.picking.batch' && this?.picking?.picking_type_code == 'outgoing') {
            await super.validate();
            this.action.doAction("stock_barcode_picking_batch.stock_barcode_batch_picking_action_kanban", {
            });

        }else if(this.resModel == 'stock.picking' && this?.record?.picking_type_code == 'outgoing'){
            await this.updatePickedForAllLines()
            this.action.doAction("stock_barcode.stock_picking_action_kanban", {
            });
        }else {
            return await super.validate();
        }
    },

    async updatePickedForAllLines(){
        let self = this
        if(this?.currentState?.lines.length > 0){
            const res = await self.orm.call(
                'stock.move.line',
                'update_picked_after_validate_delivery',
                [self?.currentState?.lines.map(move_line => move_line.id)]
            );
            return res
        }


    }
});