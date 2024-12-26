odoo.define('pos_all_in_one.LLocationSummaryReceipt', function(require) {
	'use strict';

	const PosComponent = require('point_of_sale.PosComponent');
	const Registries = require('point_of_sale.Registries');

	class LocationReceipt extends PosComponent {
		setup() {
			super.setup();
		}
		
		
	}
	LocationReceipt.template = 'LocationReceipt';

	Registries.Component.add(LocationReceipt);

	return LocationReceipt;
});