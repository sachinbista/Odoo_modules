odoo.define('bista_salesperson_enhancement.PosOrderInherit', function (require) {
"use strict";

var core = require('web.core');
var utils = require('web.utils');

var QWeb = core.qweb;
var _t = core._t;

const Registries = require('point_of_sale.Registries');
const { Order} = require('point_of_sale.models');

const PosOrderInherit = (Order) => class PosOrderInherit extends Order {
    init_from_JSON(json) {
        super.init_from_JSON(...arguments);
        this.set_sales_person(json.other_users);
        this.set_sales_person_names(json.sales_person_names)

    }
    set_sales_person_names(sales_person_names){
        this.sales_person_names = sales_person_names || null;
    }

    set_sales_person(other_users) {
        this.other_users = other_users || null;
    }

    get_sales_person() {
        return this.other_users;
    }

    get_sales_person_names() {
        return this.sales_person_names;
    }

    export_as_JSON(){
        const json = super.export_as_JSON(...arguments);
        json.other_users = this.get_sales_person();
        json.sales_person_names = this.sales_person_names;
        return json
    }
}
Registries.Model.extend(Order, PosOrderInherit);

});