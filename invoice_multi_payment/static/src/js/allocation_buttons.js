odoo.define('invoice_multi_payment.allocation_buttons', function (require) {
    "use strict";

    var ListController = require('web.ListController');
    var ListView = require('web.ListView');
    var rpc = require('web.rpc');
    var viewRegistry = require('web.view_registry');
    var core = require('web.core');
    var _t = core._t;


    // allocate amount button code
    function renderAllocateAmount() {
        if (this.$buttons) {
            var self = this;
            var response;
            var context = self.initialState.getContext();
            this.$buttons.on('click', '.o_allocate_amount', function () {
                rpc.query({
                    model: 'account.payment',
                    method: 'select_all_invoice',
                    args: [0 ,context.active_id],
                }).then(function (data) {
                    response =  data
                    self.trigger_up('reload');
                });

                setTimeout(() => {
                    var type = 'success'
                    if (response){
                        type = 'warning'
                    }else{
                        response = 'Allocated successfully'
                    }
                    self.displayNotification({
                       type: type,
                       title: _t(type),
                       message: response
                    });
                }, "1000");
            });

    this.$buttons.on('click', '.o_deallocate_amount', function () {
        rpc.query({
            model: 'account.payment',
            method: 'deselect_all_invoce',
            args: [0 ,context.active_id],
        }).then(function (data) {
                response =  data
                self.trigger_up('reload');
            });

            setTimeout(() => {
                var type = 'success'
                if (response){
                    type = 'warning'
                }else{
                    response = 'Deallocated successfully'
                }
                self.displayNotification({
                   type: type,
                   title: _t(type),
                   message: response
                });
            }, "1000");
    });

    this.$buttons.on('click', '.o_allocate_discount_amount', function () {
        rpc.query({
            model: 'account.payment',
            method: 'allocate_discount_amount',
            args: [0 ,context.active_id],
        }).then(function (data) {
            response =  data
            self.trigger_up('reload');
        });

        setTimeout(() => {
            var type = 'success'
            if (response){
                type = 'warning'
            }else{
                response = 'Discount allocated successfully'
            }
            self.displayNotification({
               type: type,
               title: _t(type),
               message: response
            });
        }, "1000");
    });


            this.$buttons.on('click', '.o_clear_selection', function () {
                rpc.query({
                    model: 'account.payment',
                    method: 'clear_selection',
                    args: [0 ,context.active_id],
                }).then(function () {
                    self.trigger_up('reload');
                });
            });

            this.$buttons.on('click', '.o_update_amounts', function () {
                rpc.query({
                    model: 'account.payment',
                    method: 'update_amounts',
                    args: [0 ,context.active_id],
                }).then(function () {
                    self.trigger_up('reload');
                });
            });

            this.$buttons.on('click', '.o_update_invoices', function () {
                rpc.query({
                    model: 'account.payment',
                    method: 'action_open_common_view',
                    args: [0 ,context.active_id],
                }).then(function () {
                    self.trigger_up('reload');
                });
            });

        if (this.$buttons) {
            var self = this;
            var context = self.initialState.getContext();
            this.$buttons.on('click', '.o_process_payment', function () {
                self.do_action({
                    name: 'Payment Process',
                    type: 'ir.actions.act_window',
                    view_mode: 'form',
                    res_model: 'common.payment.process',
                    target: 'new',
                    views: [[false, 'form']],
                    context: context
                });
            });
            }

        }
    }

    var AllocateAmountListController = ListController.extend({
        buttons_template: 'AllocateAmount.buttons',
        renderButtons: function () {
            this._super.apply(this, arguments);
            renderAllocateAmount.apply(this, arguments);
        }
    });

    var AllocateAmountListView = ListView.extend({
        config: _.extend({}, ListView.prototype.config, {
            Controller: AllocateAmountListController,
        })
    });

//    // de-allocate amount button code
//    function renderDeAllocateAmount() {
//        if (this.$buttons) {
//            var self = this;
//            var context = self.initialState.getContext();
//            this.$buttons.on('click', '.o_deallocate_amount', function () {
//                rpc.query({
//                    model: 'account.payment',
//                    method: 'deselect_all_invoce',
//                    args: [0 ,context.active_id],
//                });
//            });
//
//        }
//    }
//
//    var DeAllocateAmountListController = ListController.extend({
//        buttons_template: 'DeAllocateAmount.buttons',
//        renderButtons: function () {
//            this._super.apply(this, arguments);
//            renderDeAllocateAmount.apply(this, arguments);
//        }
//    });

//    var DeAllocateAmountListView = ListView.extend({
//        config: _.extend({}, ListView.prototype.config, {
//            Controller: DeAllocateAmountListController,
//        })
//    });

    viewRegistry.add('invoice_multi_payment_allocation_amount', AllocateAmountListView);
//    viewRegistry.add('invoice_multi_payment_deallocation_amount', DeAllocateAmountListView);
});
