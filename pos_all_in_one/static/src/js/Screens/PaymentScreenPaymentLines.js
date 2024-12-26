odoo.define('pos_all_in_one.PaymentScreenPaymentLines', function(require) {
    'use strict';

    const PaymentScreenPaymentLines = require('point_of_sale.PaymentScreenPaymentLines');
    const Registries = require('point_of_sale.Registries');
    const { useListener } = require("@web/core/utils/hooks");
     const { useState, useRef , onMounted } = owl;

    const PosPaymentScreenPaymentLines = PaymentScreenPaymentLines =>
        class extends PaymentScreenPaymentLines {
            setup() {
                super.setup();
            }
            changeInput(event){
                let order = this.env.pos.get_order();
                let pl = order.selected_paymentline;
                var inputString = $("#Input").val();
                if(inputString){
                    pl.set_pos_reference(inputString);
                }else{
                    pl.set_pos_reference(pl.pos_reference);
                }
            }
        };

    Registries.Component.extend(PaymentScreenPaymentLines, PosPaymentScreenPaymentLines);

    return PaymentScreenPaymentLines;
});