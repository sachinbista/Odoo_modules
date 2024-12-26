/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { FormController } from "@web/views/form/form_controller";
import { ListController } from "@web/views/list/list_controller";
import { useService } from "@web/core/utils/hooks";
import { _t } from 'web.core';
var rpc = require('web.rpc');

var response;
var this_data;
patch(ListController.prototype, "common_allocation", {
        setup(){
            this._super.apply();
//          this.action = useService("action")
            this.notificationService = useService("notification");
            this_data = this;
        },
        onClickUpdateInvoice(ev){
            var self = this;
            var active_id = self.model.rootParams.context.active_id;

           rpc.query({
                model: 'account.payment',
                method: 'action_open_common_view',
                args: [0 ,active_id],
            }).then(function () {
//                self.trigger_up('reload');
                return this_data.actionService.doAction({
                    type: "ir.actions.act_window",
                    res_model: 'common.allocation',
//                    res_id: active_id,
                    views: [[false, "list"]],
                    target: "current",
                    active_id: active_id,
                    display_name:'Update Invoice',
                    domain: [['linked_payment_id', '=', active_id]],
                    context: {
                        active_id: active_id,
                    },
                    clearBreadcrumbs: true,
                });
            });
       },
       onClickAllocateAmount(ev){
            var self = this;
            var active_id = self.model.rootParams.context.active_id;
            rpc.query({
                model: 'account.payment',
                method: 'select_all_invoice',
                args: [0 ,active_id],
            }).then(function (data) {
                response =  data
                return this_data.actionService.doAction({
                    type: "ir.actions.act_window",
                    res_model: 'common.allocation',
//                    res_id: active_id,
                    views: [[false, "list"]],
                    target: "current",
                    active_id: active_id,
                    display_name:'Allocate',
//                    on_reverse_breadcrumb: () => false,
                    domain: [['linked_payment_id', '=', active_id]],
                    context: {
                        active_id: active_id,
                    },

                },{
                        clearBreadcrumbs: false,
                        viewType: 'activity',
                    },);
            });

            setTimeout(() => {
                var type = 'success'
                if (response){
                    type = 'warning'
                }else{
                    response = 'Allocated successfully'
                }
                this_data.notificationService.add(response,{
                   type: type
                });
            }, "1000");
       },
       onClickDeAllocateAmount(){
            var self = this;
            var active_id = self.model.rootParams.context.active_id;
            rpc.query({
                model: 'account.payment',
                method: 'deselect_all_invoce',
                args: [0 ,active_id],
            }).then(function (data) {
                response =  data
//                self.trigger_up('reload');
                return this_data.actionService.doAction({
                    type: "ir.actions.act_window",
                    res_model: 'common.allocation',
//                    res_id: active_id,
                    display_name:'De-Allocate',
                    views: [[false, "list"]],
                    target: "current",
                    domain: [['linked_payment_id', '=', active_id]],
                    context: {
                        active_id: active_id,
                    },
                });
            });

            setTimeout(() => {
                var type = 'success'
                if (response){
                    type = 'warning'
                }else{
                    response = 'Deallocated successfully'
                }
                this_data.notificationService.add(response,{
                   type: type
                });
            }, "1000");
       },
       onClickAllocateDiscountAmount(){
            var self = this;
            var active_id = self.model.rootParams.context.active_id;
            rpc.query({
                model: 'account.payment',
                method: 'allocate_discount_amount',
                args: [0 ,active_id],
            }).then(function (data) {
                response =  data
//                self.trigger_up('reload');
                return this_data.actionService.doAction({
                    type: "ir.actions.act_window",
                    res_model: 'common.allocation',
//                    res_id: active_id,
                    display_name:'Allocate Discount',
                    views: [[false, "list"]],
                    target: "current",
                    domain: [['linked_payment_id', '=', active_id]],
                    context: {
                        active_id: active_id,
                    },
                });
            });

            setTimeout(() => {
                var type = 'success'
                if (response){
                    type = 'warning'
                }else{
                    response = 'Discount allocated successfully'
                }
                this_data.notificationService.add(response,{
                   type: type
                });
            }, "1000");
       },
       onClickClear(){
            var self = this;
            var active_id = self.model.rootParams.context.active_id;
            rpc.query({
                model: 'account.payment',
                method: 'clear_selection',
                args: [0 ,active_id],
            }).then(function (data) {
                response =  data
//                self.trigger_up('reload');
                return this_data.actionService.doAction({
                    type: "ir.actions.act_window",
                    res_model: 'common.allocation',
//                    res_id: active_id,
                    display_name:'Clear',
                    views: [[false, "list"]],
                    target: "current",
                    domain: [['linked_payment_id', '=', active_id]],
                    context: {
                        active_id: active_id,
                    },
                });
            });
            setTimeout(() => {
                var type = 'success'
                if (response){
                    type = 'warning'
                }else{
                    response = 'cleared successfully'
                }
                this_data.notificationService.add(response,{
                   type: type
                });
            }, "1000");
       },

       onClickUpdateAmount(){
            var self = this;
            var active_id = self.model.rootParams.context.active_id;
            rpc.query({
                model: 'account.payment',
                method: 'update_amounts',
                args: [0 ,active_id],
            }).then(function () {
//                self.trigger_up('reload');
                return this_data.actionService.doAction({
                    type: "ir.actions.act_window",
                    res_model: 'common.allocation',
//                    res_id: active_id,
                    display_name:'Update Amount',
                    views: [[false, "list"]],
                    target: "current",
                    domain: [['linked_payment_id', '=', active_id]],
                    context: {
                        active_id: active_id,
                    },
                });
            });
       },
       onClickProcessPayment(){
            var self = this;
            var context = self.model.rootParams.context;
            this.actionService.doAction({
                name: 'Payment Process',
                type: 'ir.actions.act_window',
                view_mode: 'form',
                res_model: 'common.payment.process',
                target: 'new',
                views: [[false, 'form']],
                context: context
            });
       },
       onClickImportInvoice(){
            var self = this;
            var context = self.model.rootParams.context;
            this.actionService.doAction({
                name: 'Import Invoice In Allocation',
                type: 'ir.actions.act_window',
                view_mode: 'form',
                res_model: 'account.invoice.allocation.import',
                target: 'new',
                views: [[false, 'form']],
                context: context
            });
       }
});