odoo.define('pos_all_in_one.XMLPosCategorySummaryReceipt', function(require) {
	'use strict';

	const PosComponent = require('point_of_sale.PosComponent');
	const Registries = require('point_of_sale.Registries');

	class XMLPosCategorySummaryReceipt extends PosComponent {
		setup() {
			super.setup();
		}
		get cate_summary(){
			let categs = this.props.order.cate_summary;
			let cate_summary = [];
			$.each(categs, function( i, x ){
				if(x){
					cate_summary.push(x)
				}
			});
			return cate_summary;
		}


	}
	XMLPosCategorySummaryReceipt.template = 'XMLPosCategorySummaryReceipt';

	Registries.Component.add(XMLPosCategorySummaryReceipt);

	return XMLPosCategorySummaryReceipt;
});
