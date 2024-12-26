odoo.define('pos_orders_all.OrderDetails', function(require) {
   'use strict';

   const OrderDetails = require('point_of_sale.OrderDetails');
   const Registries = require('point_of_sale.Registries');

   const PosOrderDetails = OrderDetails =>
       class extends OrderDetails {
           	get total_items(){
	            let lines = this.order ? this.order.orderlines.models : [];
               var total_qty = 0;
               lines.map(function(line){
                  total_qty += line.quantity;
               });

               return total_qty
	        }
       };
   Registries.Component.extend(OrderDetails, PosOrderDetails);

   return OrderDetails;
});