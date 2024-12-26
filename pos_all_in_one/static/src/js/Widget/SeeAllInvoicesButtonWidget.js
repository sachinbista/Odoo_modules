odoo.define('pos_all_in_one.SeeAllInvoicesButtonWidget', function(require) {
	'use strict';

	const PosComponent = require('point_of_sale.PosComponent');
	const ProductScreen = require('point_of_sale.ProductScreen');
	const Registries = require('point_of_sale.Registries');
	const { useListener } = require("@web/core/utils/hooks");
	let core = require('web.core');
	let _t = core._t;


	class SeeAllInvoicesButtonWidget extends PosComponent {
		setup() {
			super.setup();
			useListener('click', this.onClick);

		}
		async onClick() {
			var self = this;
			var currentOrder = self.env.pos.get_order()
			const currentPartner = currentOrder.get_partner();
			const { confirmed, payload: newPartner } = await this.showTempScreen(
				'POSInvoiceScreen',
				{ partner: currentPartner }
			);
			// this.showScreen('');
		}
	}

	SeeAllInvoicesButtonWidget.template = 'SeeAllInvoicesButtonWidget';

	ProductScreen.addControlButton({
		component: SeeAllInvoicesButtonWidget,
		condition: function() {
			return this.env.pos.config.allow_pos_invoice;
		},
	});

	Registries.Component.add(SeeAllInvoicesButtonWidget);

	return SeeAllInvoicesButtonWidget;
});