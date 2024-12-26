odoo.define('pos_orders_all.CreateSale', function(require) {
	'use strict';

	const PosComponent = require('point_of_sale.PosComponent');
	const ProductScreen = require('point_of_sale.ProductScreen');
	const { useListener } = require("@web/core/utils/hooks");
	let core = require('web.core');
	const { _t } = require('web.core')
	const Registries = require('point_of_sale.Registries');


	class CreateSale extends PosComponent {
		setup() {
            super.setup();
            useListener('click', this.onClick);
        }
		async onClick(){
			var self = this;
			var order = self.env.pos.get_order();
			var orderlines = order.orderlines;
			var cashier_id = self.env.pos.get_cashier().id;
			var partner_id = false;
			var pos_product_list = [];

			if (order.get_partner() != null)
				partner_id = order.get_partner().id;
			
			if (!partner_id) {
				return self.showPopup('ErrorPopup', {
					title: self.env._t('Unknown customer'),
					body: self.env._t('You cannot Create Sales Order. Select customer first.'),
				});
			}

			if (orderlines.length === 0) {
				return self.showPopup('ErrorPopup', {
					title: self.env._t('Empty Order'),
					body: self.env._t('There must be at least one product in your order before Add a note.'),
				});
			}
			
			for (var i = 0; i < orderlines.length; i++) {
				var product_items = {
					'id': orderlines[i].product.id,
					'quantity': orderlines[i].quantity,
					'uom_id': orderlines[i].product.uom_id[0],
					'price': orderlines[i].price,
					'discount': orderlines[i].discount,
				};
				pos_product_list.push({'product': product_items });
			}
			
			self.rpc({
				model: 'pos.order',
				method: 'create_sales_order',
				args: [partner_id, partner_id, pos_product_list, cashier_id],
			}).then(function(output) {
				while(order.get_orderlines().length > 0){
                    var line = order.get_selected_orderline();
                    order.remove_orderline(line);
                }
                order.set_partner(null);
				self.env.pos.removeOrder(order);
				alert('Sales Order Created !!!!');
                self.showScreen('ProductScreen');
			});
		}
	}

	CreateSale.template = 'CreateSale';
	ProductScreen.addControlButton({
		component: CreateSale,
		condition: function() {
			return true;
		},
	});
	Registries.Component.add(CreateSale);
	return CreateSale;
});
