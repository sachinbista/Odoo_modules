odoo.define('bista_pos_consignment.orderline_screen', function (require) {
    'use strict';

    const POSOrderline = require('point_of_sale.Orderline');
    const Registries = require('point_of_sale.Registries');
    var { Orderline } = require('point_of_sale.models');

    const ConsignmentOrderLine = (Orderline) => class ConsignmentOrderLine extends Orderline {
        init_from_JSON(json) {
            super.init_from_JSON(...arguments);
            this.set_consignment_order(json.consignment_move);
        }

        set_consignment_order(consignment_move) {
            this.consignment_move = consignment_move;
        }

        get_consignment_order() {
            return this.consignment_move;
        }

        export_as_JSON() {
            const json = super.export_as_JSON(...arguments);
            json.consignment_move = this.get_consignment_order();
            return json;
        }
    }
    const ConsignmentOrder = (POSOrderline) =>
        class ConsignmentOrder extends POSOrderline {
            setup() {
                super.setup();
            }
            selectConsignment() {
                const isChecked = this.props.line.consignment_move;
                this.set_consignment_order(!isChecked);
            }
            set_consignment_order(consignment_move) {
                this.props.line.set_consignment_order(consignment_move);
            }
        }

    Registries.Component.extend(POSOrderline, ConsignmentOrder);
    Registries.Model.extend(Orderline, ConsignmentOrderLine);
});

