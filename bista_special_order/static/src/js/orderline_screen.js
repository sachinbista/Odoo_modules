odoo.define('bista_special_order.orderline_screen', function (require) {
    'use strict';

    const POSOrderline = require('point_of_sale.Orderline');
    const Registries = require('point_of_sale.Registries');
    var {Orderline} = require('point_of_sale.models');

    const SpecialOrderLine = (Orderline) => class SpecialOrderLine extends Orderline {
        init_from_JSON(json) {
            super.init_from_JSON(...arguments);
            this.set_special_order(json.is_special);
        }

        set_special_order(is_special) {
            this.is_special = is_special;
        }

        get_special_order() {
            return this.is_special;
        }

        export_as_JSON() {
            const json = super.export_as_JSON(...arguments);
            json.is_special = this.get_special_order();
            return json;
        }
    }

    const SpecialOrder = (POSOrderline) =>
        class SpecialOrder extends POSOrderline {
            setup() {
                super.setup();
            }

            selectLine(event) {
                super.selectLine();
                if (event.target.classList.contains('check_is_special')) {
                    const isChecked = this.props.line.is_special;
                    this.set_special_order(!isChecked);
                }
        }
            set_special_order(is_special) {
                this.props.line.set_special_order(is_special);
            }
        }

    Registries.Component.extend(POSOrderline, SpecialOrder);
    Registries.Model.extend(Orderline, SpecialOrderLine);
});


