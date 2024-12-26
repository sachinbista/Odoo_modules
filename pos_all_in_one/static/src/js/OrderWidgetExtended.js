odoo.define('pos_all_in_one.LoyaltyOrderWidgetExtended', function(require){
	'use strict';

	const OrderWidget = require('point_of_sale.OrderWidget');
	const PosComponent = require('point_of_sale.PosComponent');
	const Registries = require('point_of_sale.Registries');

	const OrderWidgetExtended = (OrderWidget) =>
		class extends OrderWidget {

			get loyalty_points(){
				let order = this.env.pos.get_order();
				let loyalty_points = order ? order.get_total_loyalty() : 0;
				return loyalty_points;
			}

			get partner(){
				let order = this.env.pos.get_order();
				return order.get_partner();
			}

			get temp_loyalty_point(){
				let order = this.env.pos.get_order();
				let partner = order.get_partner();
				let loyalty_points = order ? order.get_total_loyalty() : 0;
				let temp_loyalty_point = 0

				if(partner){
					temp_loyalty_point = partner.loyalty_points1;
				}
				if(this.env.pos.pos_loyalty_setting.length != 0)
				{
					if (partner) {
						if(order.remove_true == true){
							partner.loyalty_points1 = partner.loyalty_points1
							order.update_after_redeem = partner.loyalty_points1
						}else{
							if(order.update_after_redeem >= 0){
								partner.loyalty_points1 = order.update_after_redeem;
							}else{
								partner.loyalty_points1 = partner.loyalty_points1
							}
						}
						temp_loyalty_point = partner.loyalty_points1 + loyalty_points ;				
					}
				}
				return temp_loyalty_point;
			}
		};

	Registries.Component.extend(OrderWidget, OrderWidgetExtended);

	return OrderWidget;

});