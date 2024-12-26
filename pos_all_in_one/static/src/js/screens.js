odoo.define("pos_all_in_one.screens", function(require){
	"use strict";
	
	var PosDB = require("point_of_sale.DB");
	const { PosGlobalState, Order, Orderline, Payment } = require('point_of_sale.models');
	const Registries = require('point_of_sale.Registries');
	var utils = require('web.utils');

	const PosHomePosGlobalState = (PosGlobalState) => class PosHomePosGlobalState extends PosGlobalState {
		async _processData(loadedData) {
			await super._processData(...arguments);
			let self = this;
			self._loadProductTemplate(loadedData['product.template']);
		}

		_loadProductTemplate(template){
			var self = this
			self.product_templates = template;
			self.db.add_product_templates(self.product_templates);
		}
	}
	Registries.Model.extend(PosGlobalState, PosHomePosGlobalState);
	
	PosDB.include({
		init: function(options){
			this.product_template_by_id = {};
			this.product_tmpl_id = []
			this._super(options);
		},
		add_product_templates: function(product_templates){
			for(var temp=0 ; temp < product_templates.length; temp++){
				var product_template_attribute_value_ids = [];
				var prod_temp =  product_templates[temp] ; 
				this.product_template_by_id[prod_temp.id] = prod_temp;
				this.product_tmpl_id.push(prod_temp)
				for (var prod = 0; prod <prod_temp.product_variant_ids.length; prod++){
					var product = this.product_by_id[prod_temp.product_variant_ids[prod]]
					console.log("Product variant id", prod_temp.product_variant_ids[prod])
					if (product) {
                        console.log("if found Product variant id", prod_temp.product_variant_ids[prod])
                        for (var i = 0; i < product.product_template_attribute_value_ids.length; i++){
                            product_template_attribute_value_ids.push(product.product_template_attribute_value_ids[i]);
                        }
                        product.template_name = prod_temp.name
                        product.product_variant_count = prod_temp.product_variant_count;
                    }
				}
				const unique_attribute_value_ids = [...new Set(product_template_attribute_value_ids)]
				this.product_template_by_id[prod_temp.id].product_template_attribute_value_ids = unique_attribute_value_ids;
			}
		},

        get_product_by_category_variants: function(category_id){
	        var product_ids  = this.product_by_category_id[category_id];
	        var list = [];
	        var temp = this.product_tmpl_id;
	        var product_tmpl_lst = []
	        if (product_ids) {
	            for (var i = 0; i < temp.length; i++) {
	                for (var j = 0 ; j < product_ids.length ; j++){
	                    var prd_prod = this.product_by_id[product_ids[j]]
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
	    },

	    /* returns a list of products with :
	     * - a category that is or is a child of category_id,
	     * - a name, package or barcode containing the query (case insensitive) 
	     */
	    search_product_in_category: function(category_id, query){
	        try {
	            query = query.replace(/[\[\]\(\)\+\*\?\.\-\!\&\^\$\|\~\_\{\}\:\,\\\/]/g,'.');
	            query = query.replace(/ /g,'.+');
	            var re = RegExp("([0-9]+):.*?"+utils.unaccent(query),"gi");
	        }catch(e){
	            return [];
	        }
	        var results = [];
	        var product_tmpl_lst = []
	        var temp = this.product_tmpl_id;
	        for(var i = 0; i < this.limit; i++){
	            var r = re.exec(this.category_search_string[category_id]);
	            if(r){
	                var id = Number(r[1]);
	                var prod  = this.get_product_by_id(id)
	                for(var j = 0; j < temp.length ; j++){
	                    if(jQuery.inArray( prod.product_tmpl_id, product_tmpl_lst ) == -1){
	                        if(prod.product_tmpl_id == temp[j].id){
	                            var prd_list = temp[i].product_variant_ids.sort();
	                            results.push(prod)
	                            product_tmpl_lst.push(temp[j].id)
	                        }
	                    }
	                }
	            }else{
	                break;
	            }
	        }
	        return results;
	    },
	});
});
