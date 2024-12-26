odoo.define('pos_all_in_one.CreatePaymentButtonWidget', function(require) {
	'use strict';

	const PosComponent = require('point_of_sale.PosComponent');
	const ProductScreen = require('point_of_sale.ProductScreen');
	const { useListener } = require("@web/core/utils/hooks");
	let core = require('web.core');
	let _t = core._t;
	const Registries = require('point_of_sale.Registries');

	class CreatePaymentButtonWidget extends PosComponent {
		setup() {
			super.setup();
			useListener('click', this.onClick);
		}

		async onClick() {
			var self = this;
			var currentOrder = self.env.pos.get_order()
			const currentPartner = currentOrder.get_partner();
			const { confirmed, payload: newClient } = await this.showTempScreen(
				'PartnerListScreen',
				{ client: currentPartner }
			);
			// this.showScreen('ClientListScreen');
		}
	}

	CreatePaymentButtonWidget.template = 'CreatePaymentButtonWidget';

	ProductScreen.addControlButton({
		component: CreatePaymentButtonWidget,
		condition: function() {
			return this.env.pos.config.allow_pos_payment;
		},
	});

	Registries.Component.add(CreatePaymentButtonWidget);

	return CreatePaymentButtonWidget;
});