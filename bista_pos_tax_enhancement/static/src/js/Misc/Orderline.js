odoo.define('bista_pos_tax_enhancement.pos', function(require) {
	"use strict";

	const { PosGlobalState, Order, Orderline, Payment } = require('point_of_sale.models');
    const Registries = require('point_of_sale.Registries');
    var core = require('web.core');
	var utils = require('web.utils');
    var round_pr = utils.round_precision;

	const PosCustomTaxOrderLine = (Orderline) => class PosCustomTaxOrderLine extends Orderline{
		get_all_prices(){
			super.get_all_prices(...arguments);
			if(this.discount_type){
				if (this.discount_type == 'Percentage')
				{
					var price_unit = this.get_unit_price() * (1.0 - (this.get_discount() / 100.0));
				}
				if (this.discount_type == 'Fixed')
				{
					// var price_unit = this.get_unit_price() - this.get_discount();
					var price_unit = this.get_base_price()/this.get_quantity();		
				}
			}else{
				if (this.pos.config.discount_type == 'percentage')
				{
					var price_unit = this.get_unit_price() * (1.0 - (this.get_discount() / 100.0));
				}
				if (this.pos.config.discount_type == 'fixed')
				{
					// var price_unit = this.get_unit_price() - this.get_discount();
					var price_unit = this.get_base_price()/this.get_quantity();		
				}
			}	
			var taxtotal = 0;
			var  partner_id = this.order.get_partner()
			var customer_type = ['wholesaler', 'retailer']
			var product =  this.get_product();
			var taxes_ids = product.taxes_id
			if (partner_id !== null && customer_type.includes(partner_id.customer_type)) {
				if (partner_id.customer_type === product.pos_type_tax) {

					taxes_ids[0]= product.pos_type_tax === 'wholesaler' ? 3 : 4;
				}
				else{
					taxes_ids ={}
				}

			} 
			else if (product.pos_type_tax === 'no_tax') {
				taxes_ids={}
			} 
			else {
				if (product.pos_type_tax === 'retailer') {
					taxes_ids[0] = 4;
    			} else if (product.pos_type_tax === 'wholesaler') {
        			taxes_ids[0] = 3;
    			}
			}
			var taxes =  this.pos.taxes;
			var taxdetail = {};
			var product_taxes = [];

			_(taxes_ids).each(function(el){
				product_taxes.push(_.detect(taxes, function(t){
					return t.id === el;
				}));
			});

			var all_taxes = this.compute_all(product_taxes, price_unit, this.get_quantity(), this.pos.currency.rounding);
			var all_taxes_before_discount = this.compute_all(product_taxes, this.get_unit_price(), this.get_quantity(), this.pos.currency.rounding);
			_(all_taxes.taxes).each(function(tax) {
				taxtotal += tax.amount;
				taxdetail[tax.id] = tax.amount;
			});

			return {
				"priceWithTax": all_taxes.total_included,
	            "priceWithoutTax": all_taxes.total_excluded,
	            "priceSumTaxVoid": all_taxes.total_void,
	            "priceWithTaxBeforeDiscount": all_taxes_before_discount.total_included,
	            "tax": taxtotal,
	            "taxDetails": taxdetail,
			};
		
		}
	}

	Registries.Model.extend(Orderline, PosCustomTaxOrderLine);

});
