odoo.define('bista_pos_order_notes.OrderInheritNotes', function (require) {
"use strict";

var core = require('web.core');
var utils = require('web.utils');

var QWeb = core.qweb;
var _t = core._t;

const Registries = require('point_of_sale.Registries');
const { Order} = require('point_of_sale.models');


const OrderInheritNotes = (Order) => class OrderInheritNotes extends Order {
    init_from_JSON(json) {
        super.init_from_JSON(...arguments);
        this.set_order_note(json.order_note);
    }

    set_order_note(order_note){
        this.order_note = order_note || null;
    }

    get_order_note(){
        return this.order_note
    }

    export_as_JSON(){
        const json = super.export_as_JSON(...arguments);
        json.order_note = this.get_order_note();
        return json
    }
    export_for_printing() {
        var self = this
        var json = super.export_for_printing(...arguments);
        json.order_note = self.order_note
        return json;
  }

}
Registries.Model.extend(Order, OrderInheritNotes);

});
