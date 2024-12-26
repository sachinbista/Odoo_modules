odoo.define('pos_all_in_one.ProductsWidget', function(require) {
	"use strict";

	const Registries = require('point_of_sale.Registries');
	const ProductsWidget = require('point_of_sale.ProductsWidget');
	const {Product} = require('point_of_sale.models');
	const { onMounted } = owl;


	const BiProductsTemplateWidget = (ProductsWidget) =>
		class extends ProductsWidget {
			setup() {
				super.setup();
				var self = this;
				onMounted(() => this._mounted());
			}

			_mounted() {
				var self = this;
				self.env.services['bus_service'].addEventListener('notification', ({ detail: notifications }) => {
					self.syncProdData(notifications);
				});
			}

			syncProdData(notifications){
				let self = this;
				notifications.forEach( async function (ntf) {
					ntf = JSON.parse(JSON.stringify(ntf))
					if(ntf && ntf.type && ntf.type == "product.product/sync_data"){
						let prod = ntf.payload.product[0];
						let old_category_id = self.env.pos.db.product_by_id[prod.id];
						let new_category_id = prod.pos_categ_id[0];
						let stored_categories = self.env.pos.db.product_by_category_id;

						prod.pos = self.env.pos;
						if(self.env.pos.db.product_by_id[prod.id]){
							if(old_category_id.pos_categ_id){
								stored_categories[old_category_id.pos_categ_id[0]] = stored_categories[old_category_id.pos_categ_id[0]].filter(function(item) {
									return item != prod.id;
								});
							}
							if(stored_categories[new_category_id]){
								stored_categories[new_category_id].push(prod.id);
							}
							let updated_prod = self.updateProd(prod);
						}else{

							const loadedData = await self.env.services.rpc({
					            model: 'pos.session',
					            method: 'load_pos_data_prod_temp',
					            args: [[odoo.pos_session_id]],
					        });
							let updated_prod = self.updateProd(prod);
					        await self.env.pos._loadProductTemplate(loadedData['product.template']);
						}
					}
				});
				let call = self.productsToDisplay;
				self.env.pos.is_sync = true;
			}

			updateProd(product){
				let self = this;
				product.product_tmpl_id = product.product_tmpl_id[0] || [];
				self.env.pos._loadProductProduct([product]);
				const productMap = {};
				const productTemplateMap = {};

				product.pos = self.env.pos; 
				product.applicablePricelistItems = {};
				productMap[product.id] = product;
				productTemplateMap[product.product_tmpl_id[0]] = (productTemplateMap[product.product_tmpl_id[0]] || []).concat(product);
				let new_prod =  Product.create(product);
				for (let pricelist of self.env.pos.pricelists) {
					for (const pricelistItem of pricelist.items) {
						if (pricelistItem.product_id) {
							let product_id = pricelistItem.product_id[0];
							let correspondingProduct = productMap[product_id];
							if (correspondingProduct) {
								self.env.pos._assignApplicableItems(pricelist, correspondingProduct, pricelistItem);
							}
						}
						else if (pricelistItem.product_tmpl_id) {
							let product_tmpl_id = pricelistItem.product_tmpl_id[0];
							let correspondingProducts = productTemplateMap[product_tmpl_id];
							for (let correspondingProduct of (correspondingProducts || [])) {
								self.env.pos._assignApplicableItems(pricelist, correspondingProduct, pricelistItem);
							}
						}
						else {
							for (const correspondingProduct of product) {
								self.env.pos._assignApplicableItems(pricelist, correspondingProduct, pricelistItem);
							}
						}
					}
				}
				self.env.pos.db.product_by_id[product.id] = new_prod ;
				self.env.pos.db.add_products(new_prod);
				self.productsToDisplay
			}

			get is_sync() {
				return this.env.pos.is_sync;
			}


			get productsToDisplay() {
				let self = this;
				let product_ids = super.productsToDisplay;

				if(self.env.pos.config.allow_product_variants){

					var list = [];
					var temp = this.env.pos.product_templates;
					var product_tmpl_lst = []
					if (product_ids) {
						for (var i = 0; i < temp.length; i++) {
							for (var j = 0 ; j < product_ids.length ; j++){
								var prd_prod = product_ids[j]
								if(jQuery.inArray( prd_prod.product_tmpl_id, product_tmpl_lst ) == -1){
									if(prd_prod.product_tmpl_id == temp[i].id){
										var prd_list = temp[i].product_variant_ids.sort();
										list.push(prd_prod)
										product_tmpl_lst.push(temp[i].id)
									}
								}
							}
						}
					}
					return list;
				}
				else{
					return product_ids
				}
			}
		};

	Registries.Component.extend(ProductsWidget, BiProductsTemplateWidget);

	return ProductsWidget;

});