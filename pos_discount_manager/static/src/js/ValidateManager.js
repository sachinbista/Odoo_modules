odoo.define('pos_discount_manager.ValidateManager', function(require) {
    'use strict';

  const Registries = require('point_of_sale.Registries');
  const PaymentScreen = require('point_of_sale.PaymentScreen');
  var rpc = require('web.rpc');

     const ValidateManagers = (PaymentScreen) =>
        class extends PaymentScreen {
                /**
                *Override the validate button to approve discount limit
                */
            async _finalizeValidation() {
                var order = this.env.pos.get_order();
                var orderline_discount = 0
                var totalDiscount = 0;
                var orderlines = this.currentOrder.get_orderlines()
                    orderlines.forEach(function (orderline) {
                    const discount = orderline.discount;
                    if (discount > orderline_discount) {
                    orderline_discount = discount;
                    }
                    });

                    orderlines.forEach(function (order) {
                    const discount = parseFloat(order.discount);
                    if (!isNaN(discount)) {
                        totalDiscount += discount;
                    }
                    });

                var employee_dis = this.env.pos.get_cashier()['limited_discount'];
                var employee_name = this.env.pos.get_cashier()['name']
                var flag = 1;
                 orderlines.forEach((order) => {
                   if(order.discount > employee_dis)
                   flag = 0;
                 });
                 if (flag != 1) {
                 const {confirmed,payload} = await this.showPopup('NumberPopup', {
                            title: this.env._t(employee_name + ', your discount is over the limit. \n Manager pin for Approval'),
                        });
                        if(confirmed){
                        var employee_id = this.env.pos.get_cashier()['id']
                        const manager = await this.rpc({
                               model: 'hr.employee',
                               method: 'employee_detailes_in_pos',
                               args : [employee_id]
                        });
                         var output = this.env.pos.employees.filter((obj) => obj.id == manager);
                         if (output != false &&  Sha1.hash(payload) == output[0].pin && (output[0].limited_discount >= orderline_discount && output[0].limited_discount >= totalDiscount)) {
                            this.showScreen(this.nextScreen);
                            }
                            else {
                                this.showPopup('ErrorPopup', {
                                    title: this.env._t(" Manager Restricted your discount"),
                                    body: this.env._t(employee_name + ", Your Manager pin is incorrect or Manager discount limit is exceed."),

                                });
                                return false;
                            }
                        }
                        else {
                            return false;
                        }
                        }
                        this.currentOrder.finalized = true;
                        this.showScreen(this.nextScreen);
                        super._finalizeValidation();
                        // If we succeeded in syncing the current order, and
                       // there are still other orders that are left unsynced,
                      // we ask the user if he is willing to wait and sync them.
            }
        }
     Registries.Component.extend(PaymentScreen, ValidateManagers);
     return ValidateManagers;
});