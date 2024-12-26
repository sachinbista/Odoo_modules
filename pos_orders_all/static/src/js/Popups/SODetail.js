odoo.define('pos_orders_all.SODetail', function(require) {
	'use strict';

	const Registries = require('point_of_sale.Registries');
	const AbstractAwaitablePopup = require('point_of_sale.AbstractAwaitablePopup');

	class SODetail extends AbstractAwaitablePopup {
		setup() {
            super.setup();
		}

		back() {
			this.env.posbus.trigger('close-popup', {
                popupId: this.props.id,
                response: { confirmed: false, payload: null },
            });
		}

	}
	
	SODetail.template = 'SODetail';
	Registries.Component.add(SODetail);
	return SODetail;
});
