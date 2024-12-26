/** @odoo-module **/

import {patch} from "@web/core/utils/patch";
import {Many2OneField} from "@web/views/fields/many2one/many2one_field";

const {onMounted, onWillUpdateProps} = owl;
const rpc = require('web.rpc');

patch(Many2OneField.prototype, "bista_mrp_cost.bom_cost_check", {

    setup() {
        this._super(...arguments)

        onWillUpdateProps(async (nextProps) => {
            if (this.element && nextProps.value.length) {
                this.highlight(nextProps.value[0])
            }
        })


        onMounted(async () => {
            this.element = $(this.__owl__.bdom.parentEl)
            this.parent = this.element.parent()
            this.highlight(this.resId)
        })
    },


    highlight(resId) {
        if (!this.props || !this.props.record) {
            return
        }
        if (this.props.record.resModel === "mrp.production" && this.relation === "mrp.bom" && resId) {
            this.parent.removeClass("o_attention")
            let fields = [
                'mrp_labor_cost',
                'mrp_labor_account',
                'mrp_overhead_cost',
                'mrp_overhead_account']
            rpc.query({
                model: this.relation,
                method: 'read',
                args: [resId, fields],
            }).then(function (res) {
                let bom = res[0]
                let span = this.parent.find(".fa-exclamation")
                let span_exists = span.length
                if (!span_exists) {
                    span = $("<span class='fa fa-exclamation align-self-center'><div class='o-popup oe_read_only'><div class='o-popup-header'>Missing Fields</div><ul></ul></div></span>")
                }

                let item_list = span.find("ul")
                if (!bom.mrp_labor_cost) {
                    item_list.append($("<li>Labor Cost</li>"))
                }
                if (!bom.mrp_labor_account) {
                    item_list.append($("<li>Labor Account</li>"))
                }
                if (!bom.mrp_overhead_cost) {
                    item_list.append($("<li>Overhead Cost</li>"))
                }
                if (!bom.mrp_overhead_account) {
                    item_list.append($("<li>Overhead Account</li>"))
                }
                let item_missing = item_list.find("li")
                if (item_missing.length) {
                    this.parent.addClass("o_attention")
                    if (!span_exists) {
                        this.element.before(span)
                    }
                }

            }.bind(this));
        }

    }


});
