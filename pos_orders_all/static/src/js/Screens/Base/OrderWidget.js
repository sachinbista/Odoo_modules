odoo.define('pos_orders_all.OrderWidgetExtended', function(require){
	'use strict';

	const OrderWidget = require('point_of_sale.OrderWidget');
   const Registries = require('point_of_sale.Registries');


   const PosOrderWidget = OrderWidget =>
	   	class extends OrderWidget {
			setup() {
				super.setup();
				this._updateSummary();
			}

			get order() {
				this._updateSummary();
				return this.env.pos.get_order();
			}

			_updateSummary(){
			   var self = this;
			   var order = this.env.pos.get_order();
			   var lines = order.get_orderlines();

			   var total_qty = 0;
			   lines.map(function(line){
				   total_qty += line.quantity;
			   });

			   order.set_total_items(total_qty);
		   }

			get total_items(){
				var order = this.env.pos.get_order();
				return order.get_total_items();
			}
	   	};
   Registries.Component.extend(OrderWidget, PosOrderWidget);

   return OrderWidget;

});