/* Copyright (c) 2016-Present Webkul Software Pvt. Ltd. (<https://webkul.com/>) */
/* See LICENSE file for full copyright and licensing details. */
/* License URL : <https://store.webkul.com/license.html/> */
odoo.define('pos_partial_payment_extension.PaymentScreen', function (require) {
    "use strict";
    const PaymentScreen = require('pos_all_in_one.BiPaymentScreen');
    const Registries = require('point_of_sale.Registries');
    const session = require('web.session');

    const  PaymentScreenInherit = PaymentScreen => 
    class extends PaymentScreen {
            setup() {
                super.setup();
            }
            clickPayLater(){
                let self = this;
                let order = self.env.pos.get_order();
                let orderlines = order.get_orderlines();
                let partner_id = order.get_partner();
                if (!partner_id){
                    return self.showPopup('ErrorPopup', {
                        title: self.env._t('Unknown customer'),
                        body: self.env._t('You cannot perform partial payment.Select customer first.'),
                    });
                }
                else if(orderlines.length === 0){
                    return self.showPopup('ErrorPopup', {
                        title: self.env._t('Empty Order'),
                        body: self.env._t('There must be at least one product in your order.'),
                    });
                }
                else{
                    var customerPayment = this.payment_methods_from_config.filter(v => v.split_transactions === true);
                    var paymentName = customerPayment && customerPayment[0] && customerPayment[0].name;
                    if (paymentName){
                        _.each($('.paymentmethod'), function(e,i){
                        if($(e).find('.payment-name').text().trim() == paymentName){
                            $(e).find('.payment-name').trigger('click');
                        }})
                    }else{
                        return self.showPopup('ErrorPopup', {
                        title: self.env._t('Unknown Payment Method'),
                        body: self.env._t('You cannot perform partial payment.Please Configure Customer A/c Payment Method in Pos Configuration.'),
                    });
                    }
                                        
                    order.is_partial = true;
                    order.amount_due = order.get_due();
                    order.set_is_partial(true);
                    order.to_invoice = true;
                    order.finalized = false;

                    self.env.pos.push_single_order(order);
                    self.showScreen('ReceiptScreen');
                    console.log(this);                  
                }
            }
        }

    Registries.Component.extend(PaymentScreen, PaymentScreenInherit); 
   
});