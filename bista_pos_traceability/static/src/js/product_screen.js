
// BiProductScreen js
odoo.define('bista_pos_traceability.ProductScreenLotinherit', function(require) {
	"use strict";

	const Registries = require('point_of_sale.Registries');
	const ProductScreen = require('point_of_sale.ProductScreen'); 

	const ProductScreenLotinherit = (ProductScreen) =>
		class extends ProductScreen {
			setup() {
	            super.setup();
	        }
	        async _getAddProductOptions(product, code) {
	        	this.env.pos.get_order().lot_product = product
	        	return super._getAddProductOptions(product, code)
	         }
		
		};

	Registries.Component.extend(ProductScreen, ProductScreenLotinherit);
});
