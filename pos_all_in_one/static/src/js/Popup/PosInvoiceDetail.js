odoo.define('pos_all_in_one.PosInvoiceDetail', function(require) {
	'use strict';

	const PosComponent = require('point_of_sale.PosComponent');
	const AbstractAwaitablePopup = require('point_of_sale.AbstractAwaitablePopup');
	const Registries = require('point_of_sale.Registries');


	class PosInvoiceDetail extends AbstractAwaitablePopup {
		setup() {
			super.setup();
			this.invoice = this.props.order;
		}
		go_back_screen() {
			this.showScreen('ProductScreen');
			this.cancel();
		}

		async register_payment() {
			var self = this;
			var invoice = this.invoice;
			this.env.posbus.trigger('close-popup', {
                popupId: this.props.id,
                response: { confirmed: false, payload: null },
            });
			self.showPopup('RegisterInvoicePaymentPopupWidget', {'invoice':this.invoice});
		}
	}
	
	PosInvoiceDetail.template = 'PosInvoiceDetail';
	Registries.Component.add(PosInvoiceDetail);
	return PosInvoiceDetail;
});
