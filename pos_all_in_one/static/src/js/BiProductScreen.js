
// BiProductScreen js
odoo.define('pos_all_in_one.BiProductScreen', function(require) {
	"use strict";

	const models = require('point_of_sale.models');
	const PosComponent = require('point_of_sale.PosComponent');
	const Registries = require('point_of_sale.Registries');
	const Session = require('web.Session');
	const chrome = require('point_of_sale.Chrome');
	const ControlButtonsMixin = require('point_of_sale.ControlButtonsMixin');
	const NumberBuffer = require('point_of_sale.NumberBuffer');
	const { onChangeOrder, useBarcodeReader } = require('point_of_sale.custom_hooks');
	const { useState } = owl;
	const { useListener } = require("@web/core/utils/hooks");
	const { Gui } = require('point_of_sale.Gui');
	const ProductScreen = require('point_of_sale.ProductScreen'); 

	const BiProductScreen = (ProductScreen) =>
		class extends ProductScreen {
			setup() {
	            super.setup();
	            useListener('click-actions', this._onClickHideButtons);
				this.show_buttons = true;
	        }
			mounted () {
				let self = this;
				
				if(this.env.pos.config.cash_control && this.env.pos.pos_session.state == 'opening_control') {
	                Gui.showPopup('CashOpeningPopup', {notEscapable: true});
	            }
	            this.env.pos.on('change:selectedClient', this.render, this);
				if(this.show_buttons){
					$('.control-buttons').show();
				}else{
					$('.control-buttons').hide();
				}
			}

			_setValue(val) {
				let allow_rmv_ol = this.env.pos.get_cashier().is_allow_remove_orderline;
				let is_allow_qty = this.env.pos.get_cashier().is_allow_qty;
				if(allow_rmv_ol == false || is_allow_qty == false){
					if(val == '' || val == 'remove'){
						alert("Sorry,You are not allowed to perform this operation");
						return
					}
				}
				
				if (this.currentOrder.get_selected_orderline()) {
					if (this.env.pos.numpadMode === 'quantity') {
						this.currentOrder.get_selected_orderline().set_quantity(val);
					} else if (this.env.pos.numpadMode === 'discount') {
						this.currentOrder.get_selected_orderline().set_discount(val);
					} else if (this.env.pos.numpadMode === 'price') {
						var selected_orderline = this.currentOrder.get_selected_orderline();
						selected_orderline.price_manually_set = true;
						selected_orderline.set_unit_price(val);
					}
					if (this.env.pos.config.iface_customer_facing_display) {
						this.env.pos.send_current_order_to_customer_facing_display();
					}
				}
			}

			_onClickHideButtons(event){
				this.show_buttons = ! this.show_buttons ;
				if(this.show_buttons){
					$('.control-buttons').show();
				}else{
					$('.control-buttons').hide();
				}
				this.render();
			}
			async _clickProduct(event) {
				var self = this;
				const product = event.detail;
				if(self.env.pos.config.allow_product_variants){
					if (product.product_variant_count > 1) {
						var prod_template = this.env.pos.db.product_template_by_id[product.product_tmpl_id];
						var prod_list = [];
						prod_template.product_variant_ids.forEach(function (prod) {
							prod_list.push(self.env.pos.db.get_product_by_id(prod));
						});			
						// this.product_template_list_widget.set_product_list(prod_list);
						this.showPopup('ProductTemplatePopupWidget', {'variant_ids':prod_list});
					} else {
						// super._clickProduct(event);
						let allow_order = self.env.pos.config.pos_allow_order;
						let pos_config = self.env.pos.config;
						let deny_order= self.env.pos.config.pos_deny_order;
						let call_super = true;
						if(self.env.pos.config.pos_display_stock)
						{
							if(self.env.pos.config.show_stock_location == 'specific' && product.type == 'product')
							{
								// var partner_id = self.env.pos.get_partner();
								var location = self.env.pos.config.stock_location_id[0];
								await this.rpc({
									model: 'stock.quant',
									method: 'get_single_product',
									args: [0,product.id, location],
								}).then(function(output) {
									if (allow_order == false)
									{
										if ( (output[0][1] <= deny_order) || (output[0][1] <= 0) )
										{
											call_super = false;
											self.showPopup('ErrorPopup', {
												title: self.env._t('Deny Order'),
												body: self.env._t("Deny Order" + "(" + product.display_name + ")" + " is Out of Stock."),
											});
										}
									}
									else if(allow_order == true)
									{
										if (output[0][1] <= deny_order)
										{
											call_super = false;
											self.showPopup('ErrorPopup', {
												title: self.env._t('Deny Order'),
												body: self.env._t("Deny Order" + "(" + product.display_name + ")" + " is Out of Stock."),
											});
										}
									}
								});
							}
							else{
								if (pos_config.pos_stock_type == 'onhand'){
									if ( product.bi_on_hand <= deny_order ){
										call_super = false;
										self.showPopup('ErrorPopup', {
											title: self.env._t('Deny Order'),
											body: self.env._t("Deny Order" + "(" + product.display_name + ")" + " is Out of Stock."),
										});
									}
								}
								if (pos_config.pos_stock_type == 'incoming'){
									if ( product.incoming_qty <= deny_order ){
										call_super = false;
										self.showPopup('ErrorPopup', {
											title: self.env._t('Deny Order'),
											body: self.env._t("Deny Order" + "(" + product.display_name + ")" + " is Out of Stock."),
										});
									}
								}
								if (pos_config.pos_stock_type == 'outgoing'){
									if ( product.outgoing_qty <= deny_order ){
										call_super = false;
										self.showPopup('ErrorPopup', {
											title: self.env._t('Deny Order'),
											body: self.env._t("Deny Order" + "(" + product.display_name + ")" + " is Out of Stock."),
										});
									}
								}
								if (pos_config.pos_stock_type == 'available'){
									if ( product.bi_available <= deny_order ){
										call_super = false;
										self.showPopup('ErrorPopup', {
											title: self.env._t('Deny Order'),
											body: self.env._t("Deny Order" + "(" + product.display_name + ")" + " is Out of Stock."),
										});
									}
								}
							}
						}
						if(call_super){
							super._clickProduct(event);
						}
					}
				}else{
					super._clickProduct(event);
				}
			}

			async _onClickCustomer() {
				let order = this.env.pos.get_order();
				let self = this;
				if(order.redeem_done){
					this.showPopup('ErrorPopup',{
						'title': this.env._t('Cannot Change Customer'),
						'body': this.env._t('Sorry, you redeemed product, please remove it before changing customer.'),
					}); 
				}else{
					const currentClient = this.currentOrder.get_partner();
					const { confirmed, payload: newClient } = await this.showTempScreen(
						'ClientListScreen',
						{ client: currentClient }
					);
					if (confirmed) {
						this.currentOrder.set_partner(newClient);
						this.currentOrder.updatePricelist(newClient);
					}
				}
			}
		};

	Registries.Component.extend(ProductScreen, BiProductScreen);

	return ProductScreen;

});
