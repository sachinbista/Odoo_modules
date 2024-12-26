/** @odoo-module **/

import {patch} from '@web/core/utils/patch';
import { QtyAtDatePopover } from "@sale_stock/widgets/qty_at_date_widget";

patch(QtyAtDatePopover.prototype, 'bista_list_o2m.QtyAtDatePopover', {
    openForecast() {
        if (this.actionService.currentController.view.type === 'list'){
            this.actionService.doAction("stock.stock_replenishment_product_product_action", {
                additionalContext: {
                    active_model: 'product.product',
                    active_id: this.props.record.data.product_id[0],
                    warehouse: this.props.record.data.warehouse_id && this.props.record.data.warehouse_id[0],
                    sale_line_to_match_id: this.props.record.data.id,
                },
            });
        }else {
            this._super(...arguments);
        }
    }

});

// import { patch } from '@web/core/utils/patch';

// import { QtyAtDateWidget } from "@sale_stock/widgets/qty_at_date_widget";

// patch(QtyAtDateWidget.prototype, 'bista_list_o2m.QtyAtDateWidget', {
//     initCalcData() {
//         // calculate data not in record
//         const {data} = this.props.record.parentRecord;
//         if (data.scheduled_date) {
//             // TODO: might need some round_decimals to avoid errors
//             if (this.props.record.parentRecord) {
//                 if (this.props.record.parentRecord.data.order_status === 'sale') {
//                     this.calcData.will_be_fulfilled = data.free_qty_today >= data.qty_to_deliver;
//                 } else {
//                     this.calcData.will_be_fulfilled = data.virtual_available_at_date >= data.qty_to_deliver;
//                 }
//                 this.calcData.will_be_late = data.forecast_expected_date && data.forecast_expected_date > data.scheduled_date;
//                 if (['draft', 'sent'].includes(this.props.record.parentRecord.data.state)) {
//                     // Moves aren't created yet, then the forecasted is only based on virtual_available of quant
//                     this.calcData.forecasted_issue = !this.calcData.will_be_fulfilled && !data.is_mto;
//                 } else {
//                     // Moves are created, using the forecasted data of related moves
//                     this.calcData.forecasted_issue = !this.calcData.will_be_fulfilled || this.calcData.will_be_late;
//                 }
//             } else {
//                 this._super(...arguments);
//             }
//         }
//     }
// });
