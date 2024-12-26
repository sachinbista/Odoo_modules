odoo.define('pos_all_in_one.POSInvoiceScreen', function (require) {
	'use strict';

	const { debounce } = require("@web/core/utils/timing");
	const PosComponent = require('point_of_sale.PosComponent');
	const Registries = require('point_of_sale.Registries');
	const { useListener } = require("@web/core/utils/hooks");
	const rpc = require('web.rpc');
	let core = require('web.core');
	let _t = core._t;

	class POSInvoiceScreen extends PosComponent {
		setup() {
			super.setup();
			this.state = {
				query: null,
				selectedPosOrder: this.props.partner,
			};
			useListener('click-showDetails', this.showDetails);
			this.orders = this.get_invoices()[0] || [];
			this.orderlines = this.get_invoices()[1] || [];
			this.updateOrderList = debounce(this.updateOrderList, 70);
		}
		cancel() {
			this.trigger('close-temp-screen');
		}

		async register_payment() {
			var self = this;
			const partner_id = self.state.selectedPosOrder;
			if (!partner_id) {

				self.showPopup('ErrorPopup', {
					'title': _t('Unknown customer'),
					'body': _t('You cannot Register Payment. Select Invoice first.'),
				});
				return false;
			}

			self.showPopup('RegisterPaymentPopupWidget', {'invoice':self.state.selectedPartner});
		}

		get currentOrder() {
			return this.env.pos.get_order();
		}

		get invoices() {
			let self = this;
			let query = this.state.query;
			if(query){
				query = query.trim();
				query = query.toLowerCase();
			}
			if(this.orders){
				if ((query && query !== '') || 
					(this.props.selected_partner_id)) {
					return this.search_orders(this.orders,query);
				} else {
					return this.orders;
				}
			}
			else{
				let odrs = this.get_invoices()[0] || [];
				if (query && query !== '') {
					return this.search_orders(odrs,query);
				} else {
					return odrs;
				}
			}
		}

		get pos_order_lines() {
			return this.orderlines;
		}

		search_orders(orders,query){
			let self = this;
			let selected_orders = [];
			let search_text = query;
			let selected_partner = self.props.selected_partner_id;
			orders.forEach(function(odr) {
				if ((odr.partner_id == '' || !odr.partner_id) && search_text) {
					if (((odr.name.toLowerCase()).indexOf(search_text) != -1) || 
						((odr.state.toLowerCase()).indexOf(search_text) != -1)) {
						selected_orders.push(odr);
					}
				}
				else
				{
					if(search_text){
						if (((odr.name.toLowerCase()).indexOf(search_text) != -1) || 
							((odr.state.toLowerCase()).indexOf(search_text) != -1)|| 
							((odr.partner_id[1].toLowerCase()).indexOf(search_text) != -1)) {
							selected_orders.push(odr);
						}
					}
					
					if(selected_partner){
						if (odr.partner_id[0] == selected_partner){
							selected_orders.push(odr);
						}
					}
				}
			});
			return selected_orders;
		}

		refresh_orders(){
			$('.input-search-orders').val('');
			this.state.query = '';
			this.props.selected_partner_id = false;
			this.get_invoices();
			this.render();
		}

		updateOrderList(event) {
			this.state.query = event.target.value;
			const invoices = this.invoices;
			if (event.code === 'Enter' && invoices.length === 1) {
				this.state.selectedPosOrder = invoices[0];
			} else {
				this.render();
			}
		}

		clickPosOrder(invoices) {
			let order = invoices;
			if (this.state.selectedPosOrder === order) {
				this.state.selectedPosOrder = null;
			} else {
				this.state.selectedPosOrder = order;
			}
			this.showDetails(order)
			this.render();
		}

		get_current_day() {
			let today = new Date();
			let dd = today.getDate();
			let mm = today.getMonth()+1; //January is 0!
			let yyyy = today.getFullYear();
			if(dd<10){
				dd='0'+dd;
			} 
			if(mm<10){
				mm='0'+mm;
			} 
			today = yyyy+'-'+mm+'-'+dd;
			return today;
		}

		get_inv_domain() {
			let self = this; 
			let current = self.env.pos.pos_session.id;
			let pos_config = self.env.pos.config;
			return [['state', '=', 'posted'], ['move_type','=','out_invoice'], ['payment_state', '!=', 'paid']];
		}

		async get_invoices () {
			let self = this;
			let inv_domain = self.get_inv_domain();

			var	fields = ['name','partner_id','amount_total','amount_residual','currency_id','state','payment_state']
			let load_invoice = [];
			let load_invoice_line = [];
			let inv_ids = [];
			try {
				await self.rpc({
					model: 'account.move',
					method: 'search_read',
					args: [inv_domain,fields],
				}).then(function(output) {
					load_invoice = output;					
					self.env.pos.db.invoice_by_id = {};
					load_invoice.forEach(function(inv) {
						inv_ids.push(inv.id)
						self.env.pos.db.invoice_by_id[inv.id] = inv;		
					});

					let fields_domain = [['move_id','in',inv_ids]];
					let fields = ['name','move_id']
					self.rpc({
						model: 'account.move.line',
						method: 'search_read',
						args: [fields_domain,fields],
					}).then(function(output1) {
						load_invoice_line = output1;
						self.orders = load_invoice;
						self.orderlines = output1;
						self.env.pos.db.invoice_line_id = {};
						output1.forEach(function(ol) {
							self.env.pos.db.invoice_line_id[ol.id] = ol;						
						});
						self.render();
						return [load_invoice,load_invoice_line]
					});
				}); 
			}catch (error) {
				if (error.message.code < 0) {
					await this.showPopup('OfflineErrorPopup', {
						title: this.env._t('Offline'),
						body: this.env._t('Unable to load orders.'),
					});
				} else {
					throw error;
				}
			}

		}

		showDetails(invoices){
			let self = this;
			let o_id = invoices.id;
			let orders =  self.orders;
			let orderlines =  self.orderlines;
			let orders1 = [invoices];
			
			let pos_lines = [];

			for(let n=0; n < orderlines.length; n++){
				if (orderlines[n]['move_id'][0] ==o_id){
					pos_lines.push(orderlines[n])
				}
			}
			self.showPopup('PosInvoiceDetail', {
				'order': invoices, 
				'orderline':pos_lines,
			});
		}
	}


	POSInvoiceScreen.template = 'POSInvoiceScreen';
	POSInvoiceScreen.hideOrderSelector = true;
	Registries.Component.add(POSInvoiceScreen);
	return POSInvoiceScreen;
});
