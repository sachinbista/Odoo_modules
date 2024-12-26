/** @odoo-module **/
import publicWidget from "@web/legacy/js/public/public_widget";
import {Component} from "@odoo/owl";

publicWidget.registry.websiteSaleCart.include({

    events: Object.assign({}, publicWidget.registry.websiteSaleCart.prototype.events, {
        'click .js_delete_section': '_onClickDeleteSection',
    }),

    start() {
        const def = this._super(...arguments);
        console.log("Cart ", this)
        return def;
    },


    _onClickDeleteProduct: function (ev) {
        ev.preventDefault();
        let target = $(ev.currentTarget)
        let cart = target.closest('.o_cart_product')
        let qty = cart.find('.js_quantity')
        qty.val(0).trigger('change')
    },

});
