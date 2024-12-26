/** @odoo-module **/

import {formatDateTime} from "@web/core/l10n/dates";
import {localization} from "@web/core/l10n/localization";
import {registry} from "@web/core/registry";
import {useService} from "@web/core/utils/hooks";
import {usePopover} from "@web/core/popover/popover_hook";

const {Component, EventBus, onWillRender} = owl;

//
export class BranchQtyAtDatePopover extends Component {
}

BranchQtyAtDatePopover.template = "bista_list_o2m.QtyDetailPopOver";

export class BranchQtyAtDateWidget extends Component {
    setup() {
        this.bus = new EventBus();
        this.popover = usePopover();
        this.closePopover = null;
        this.calcData = {};
        this.props.record.warehouse_qty_data = [];
        this.calcData.will_be_fulfilled = false
        onWillRender(() => {
//            this.updateProductData();
            // this.initialData(result);
        })
    }

    initialData(res) {
        const {data} = this.props.record;
        if (this.props.record.parentRecord) {
            if (['draft', 'sent', 'sale'].includes(this.props.record.parentRecord.data.order_status)) {
                var quantity, warehouse;
                if (res.length >=1){
                    for(var i in res){
                        quantity =+ res[i].qty;
                        warehouse =+ res[i].so_available
                    }
                }
                if(!quantity){
                    this.calcData.will_be_fulfilled = true;
                    // this.calcData.forecasted_issues = this.calcData.will_be_fulfilled;
                }
                if (!warehouse){
                    this.calcData.so_available = true;
                }
            }
        }
    }

    async updateProductData() {
        let self = this
        return await this.constructor.env.services.rpc({
            model: 'product.product',
            method: 'action_product_warehouse_qty',
            args: [this.props.record.data.product_id],
        }).then(result => {
            this.initialData(result);
            this.props.record.warehouse_qty_data = result;
            return result;
        }).catch(error => {
                throw error; // Re-throw the error to propagate it to the caller
        });
    }

    showPopup(ev) {
        this.updateProductData();

        this.closePopover = this.popover.add(
            ev.currentTarget,
            this.constructor.components.Popover,
            {bus: this.bus, record: this.props.record, calcData: this.calcData},
            {
                position: 'left',
            });
        this.bus.addEventListener('close-popover', this.closePopover);
    }
}

BranchQtyAtDateWidget.components = {Popover: BranchQtyAtDatePopover};
BranchQtyAtDateWidget.template = "bista_list_o2m.qtyAtDate";

registry.category("view_widgets").add("branch_qty_at_date_widget", BranchQtyAtDateWidget);






