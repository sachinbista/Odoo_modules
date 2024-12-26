odoo.define('pos_partial_payment_extension.RegisterInvoicePaymentPopupWidget', function(require) {
	'use strict';

	const AbstractAwaitablePopup = require('point_of_sale.AbstractAwaitablePopup');
	const Registries = require('point_of_sale.Registries');
	const rpc = require('web.rpc');
	let core = require('web.core');
	let _t = core._t;

	class RegisterInvoicePaymentPopupWidget extends AbstractAwaitablePopup {

		setup() {
			super.setup();
			this.invoice = this.props.invoice;
		}

		async register_payment() {
			var self = this;
			var invoice = this.invoice;
			var partner = invoice.partner_id[0];
			var payment_type = $('#payment_type1').val();
			var entered_amount = $("#entered_amount1").val();
			var entered_note = $("#entered_note1").val();
			let rpc_result = false;
            let context = {}
			if (invoice['amount_residual'] >= entered_amount){
				rpc_result = rpc.query({
					model: 'pos.create.customer.payment',
					method: 'create_customer_payment_inv',
					context: {'pos_create_payment': true },
					args: [partner ? partner : 0, partner ? partner : 0, payment_type, entered_amount, invoice, entered_note],

				}).then(function(output) {
				    self.cancel()
					self.showScreen('ProductScreen');
				});


			}else{
				self.showPopup('ErrorPopup', {
					'title': _t('Amount Error'),
					'body': _t('Entered amount is larger then due amount. please enter valid amount'),
				});
			}

		}

		cancel() {
            this.env.posbus.trigger('close-popup', {
                popupId: this.props.id,
                response: { confirmed: false, payload: null },
            });
            this.trigger('close-temp-screen');
			// this.showTempScreen('PartnerListScreen');
        }
	}

	RegisterInvoicePaymentPopupWidget.template = 'RegisterInvoicePaymentPopupWidget';

	RegisterInvoicePaymentPopupWidget.defaultProps = {
		confirmText: 'Create',
		cancelText: 'Close',
		title: 'Register Payment for the Invoice & Validate',
		body: '',
	};

	Registries.Component.add(RegisterInvoicePaymentPopupWidget);

	return RegisterInvoicePaymentPopupWidget;
});













