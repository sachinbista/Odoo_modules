odoo.define('pos_all_in_one.XMLPosPaymentSummaryReceipt', function(require) {
	'use strict';

	const PosComponent = require('point_of_sale.PosComponent');
	const Registries = require('point_of_sale.Registries');

	class XMLPosPaymentSummaryReceipt extends PosComponent {
		setup() {
			super.setup();
		}
	}
	XMLPosPaymentSummaryReceipt.template = 'XMLPosPaymentSummaryReceipt';

	Registries.Component.add(XMLPosPaymentSummaryReceipt);

	return XMLPosPaymentSummaryReceipt;
});