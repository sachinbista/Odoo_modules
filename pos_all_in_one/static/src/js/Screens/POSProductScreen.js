odoo.define('pos_all_in_one.POSProductScreen', function (require) {
	'use strict';

	const { debounce } = require("@web/core/utils/timing");
	const PosComponent = require('point_of_sale.PosComponent');
	const Registries = require('point_of_sale.Registries');
	const { useListener } = require("@web/core/utils/hooks");	
    const {  useRef, onMounted } = owl;
	const {Product} = require('point_of_sale.models');
	var rpc = require('web.rpc');

	class POSProductScreen extends PosComponent {
		// constructor() {
		// 	super(...arguments);
		// 	var self = this;
		// 	this.state = {
		// 		query: null,
		// 		selectedPosOrder: this.props.client,
		// 	};
		// 	useListener('click-showDetails', this.showDetails);
		// 	let product_dict = this.env.pos.db.product_by_id;

		// 	this.updateProductList = debounce(this.updateProductList, 70);
		//     let data = Object.keys(product_dict).map(function(k) {
		//         return product_dict[k];
		//     });
		//     this.orders = data || [];

		//     self.env.services.bus_service.updateOption('pos.sync.product',self.env.session.uid);
  //           self.env.services.bus_service.onNotification(self,self._onProductSyncNotification);
  //           self.env.services.bus_service.startPolling();
  //           self.env.services.bus_service._startElection();

		// }

		setup() {
			super.setup();
			var self = this;
			this.state = {
				query: null,
				selectedPosOrder: this.props.client,
			};
            this.searchWordInputRef = useRef('search-word-input-partner');
			useListener('click-showDetails', this.showDetails);
			let pd = this.prod_data;
		}

		back() {
            this.props.resolve({ confirmed: false, payload: false });
            this.trigger('close-temp-screen');
        }

		// _onProductSyncNotification(notifications){
  //           let self = this;
  //           notifications.forEach(function (ntf) {
  //               ntf = JSON.parse(JSON.stringify(ntf))
  //               if(ntf && ntf.type){
  //                   if (ntf.type.access == 'pos.sync.product'){
  //                       self.refresh_orders()
  //                   }
  //               }
  //           });
  //           // let call = debounce(this.updateClientList, 70);
  //           this.env.pos.set("is_sync_partner",true);
            
  //       }

  		get prod_data(){
			let product_dict = this.env.pos.db.product_by_id;
			let data = [];
			$.each( product_dict, function( key, value ) {
				if(key != 'undefined' ){
					data.push(value)
				}
			});
			this.updateProductList = debounce(this.updateProductList, 70);
			this.orders = data || [];
		}

		get AddNewProduct(){
			let product_dict = this.env.pos.db.product_by_id;
			let data = Object.keys(product_dict).map(function(k) {
		        return product_dict[k];
		    });
		    this.orders = data || [];

		}

		cancel() {
			this.props.resolve({ confirmed: false, payload: false });
			this.trigger('close-temp-screen');
		}

		get currentOrder() {
			return this.env.pos.get_order();
		}

		get pos_products() {
			let self = this;
			let query = this.state.query;
			if(query){
				query = query.trim();
				query = query.toLowerCase();
			}
			if (query && query !== '') {
				return this.search_orders(this.orders,query);
			} else {
				return this.orders;
			}
		}

		_clearSearch() {
            this.searchWordInputRef.el.value = '';
            this.state.query = '';
            this.state.searchWord = '';
			this.render(true);
        }

		search_orders(orders,query){
			let self = this;
			let selected_orders = [];
			let search_text = query;			
			orders.forEach(function(odr) {
				if (search_text) {
					if (((odr.display_name.toLowerCase()).indexOf(search_text) != -1)) {
						selected_orders.push(odr);
					}
					else if(odr.barcode != false){
						if(odr.barcode.indexOf(search_text) != -1){
							selected_orders.push(odr);
						}
					}
					else if(odr.default_code != false){
						if (((odr.default_code.toLowerCase()).indexOf(search_text) != -1)) {
							selected_orders.push(odr);
						}
					}
				}
			});
			return selected_orders;
		}

		get_orders_fields(){
			var fields = ['name','display_name','default_code','barcode','lst_price','standard_price',
				'categ_id','pos_categ_id','taxes_id','to_weight','uom_id','description_sale','tracking',
				'description','product_tmpl_id','write_date','available_in_pos','attribute_line_ids'];
			return fields;
		}

		// refresh_orders(){
			
		// 	var self = this;
		// 	var product_list = self.env.pos.db.product_by_id;
		// 	let pord_data = Object.keys(product_list).map(function(k) {
		//         return product_list[k];
		//     });
		//     this.orders = pord_data 
		// 	this.state.query = '';
		// 	this.render();
		// }

		refresh_orders(){
			let self = this;
			let pd = this.prod_data;
			this.state.query = '';
            this.searchWordInputRef.el.value = '';
			this.render();
		}

		create_order(event){
			this.showPopup('ProductDetailsCreate', {
				products : {values: null}
			})
		}

		// updateProductList(event) {
		// 	this.state.query = event.target.value;
		// 	const pos_orders = this.pos_orders;
		// 	if (event.code === 'Enter' && pos_orders.length === 1) {
		// 		this.state.selectedPosOrder = pos_orders[0];
		// 	} else {
		// 		this.render();
		// 	}
		// }

		updateProductList(event) {
			this.state.query = event.target.value;
			const pos_products = this.pos_products;
			if (event.code === 'Enter' && pos_products.length === 1) {
				this.state.selectedPosOrder = pos_products[0];
			} else {
				this.render();
			}
		}

		clickPosOrder(order) {
			if (this.state.selectedPosOrder === order) {
				this.state.selectedPosOrder = null;
			} else {
				this.state.selectedPosOrder = order;
			}
			this.showDetails(order)
			this.render();
		}

		showDetails(order){
			let self = this;
			self.showPopup('POSProductDetail', {
				'order': order, 
			});
		}
	}


	POSProductScreen.template = 'POSProductScreen';
	POSProductScreen.hideOrderSelector = true;
	Registries.Component.add(POSProductScreen);
	return POSProductScreen;
});
