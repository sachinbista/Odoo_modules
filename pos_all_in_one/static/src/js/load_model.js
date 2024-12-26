odoo.define('pos_all_in_one.pos', function (require) {
	"use strict";

	const { PosGlobalState, Order, Orderline, Payment } = require('point_of_sale.models');
	const Registries = require('point_of_sale.Registries');
	var utils = require('web.utils');
	var PosDB = require('point_of_sale.DB');

	PosDB.include({
		get_unpaid_orders: function(){
			var saved = this.load('unpaid_orders',[]);
			var orders = [];
			for (var i = 0; i < saved.length; i++) {
				let odr = saved[i].data;
				if(!odr.is_paying_partial && !odr.is_partial && !odr.is_draft_order){
					orders.push(saved[i].data);
				}
				if(odr.is_paying_partial || odr.is_partial || odr.is_draft_order){
					saved = _.filter(saved, function(o){
						return o.id !== odr.uid;
					});
				}
			}
			this.save('unpaid_orders',saved);
			return orders;
		},
	});

	const PosHomePosGlobalState = (PosGlobalState) => class PosHomePosGlobalState extends PosGlobalState {
		async _processData(loadedData) {
			await super._processData(...arguments);
			let self = this;
			self.pos_category = loadedData['pos_category'];
			self.stockwarehouse = loadedData['stock.warehouse'];
            self.stockpickingtype = loadedData['pos_stock_picking_type'];
            self.stocklocations = loadedData['stock.location'];
            self.pos_sessions = loadedData['pos_sessions'];
            self.stockpicking = loadedData['stock.picking'];
            self.pos_order = loadedData['pos_order'] || [];
            self.pos_loyalty_setting = loadedData['pos.loyalty.setting'];
			self.pos_redeem_rule = loadedData['pos.redeem.rule'];
		}
	}
	Registries.Model.extend(PosGlobalState, PosHomePosGlobalState);


	const PosOrder = (Order) => class PosOrder extends Order {
		constructor(obj, options) {
			super(...arguments);
			this.loyalty = this.loyalty  || 0;
			this.redeemed_points = this.redeemed_points || 0;
			this.redeem_done = this.redeem_done || false;
			this.remove_true = this.remove_true || false;
			this.redeem_point = this.redeem_point || 0;
			this.remove_line = this.remove_line || false;

			this.is_partial    = false;
			this.is_paying_partial    = false;
			this.amount_due    = 0;
			this.amount_paid    = 0;
			this.is_draft_order = false;
			this.set_is_partial();
		}
		
		init_from_JSON(json){
			super.init_from_JSON(...arguments);			
			this.loyalty = json.loyalty;
			this.redeem_done = json.redeem_done;
			this.redeemed_points = json.redeemed_points;
			this.remove_true = json.remove_true || false;
			this.redeem_point = json.redeem_point || 0;
			this.remove_line = json.remove_line || false;

			this.is_partial = json.is_partial;
			this.amount_due = json.amount_due;
			this.is_paying_partial = json.is_paying_partial;
			this.is_draft_order = json.is_draft_order;
		}

		export_as_JSON(){
			const json = super.export_as_JSON(...arguments);			
			json.redeemed_points = this.redeemed_points;
			json.loyalty = this.final_loyalty_value;
			json.redeem_done = this.redeem_done;
			json.remove_true = this.remove_true || false;
			json.redeem_point = this.redeem_point || 0;
			json.remove_line = this.remove_line || false;

			json.is_partial = this.is_partial || false;
			json.amount_due = this.final_due_value;
			json.is_paying_partial = this.is_paying_partial;
			json.is_draft_order = this.is_draft_order || false;
			return json;
		}
		set_loaylty_value(value){
			this.final_loyalty_value=value;
		}
		set_is_partial(set_partial){
    		this.is_partial = set_partial || false;
    	}
		set_final_due(value){
			this.final_due_value=value;
		}
    	get_partial_due(){
    		let due = 0;
			if(this.get_due() > 0){
				due = this.get_due();
			}
			return due
    	}

		remove_orderline(line) {
			this.redeem_done = false;
			if(line.id ==this.remove_line){
				this.remove_true = true;
				let partner = this.get_partner();
				if (partner) {
					partner.loyalty_points1 = partner.loyalty_points1 + parseFloat(this.redeem_point) ;
				}
			}
			else{
				this.remove_true = false;
			}
			super.remove_orderline(...arguments);
		}


		get_redeemed_points(){
			return this.redeemed_points;
		}

		get_total_loyalty(){
			let round_pr = utils.round_precision;
			let round_di = utils.round_decimals;
			let rounding = this.pos.currency.rounding;
			let final_loyalty = 0
			let order = this.pos.get_order();
			let orderlines = this.get_orderlines();
			let partner_id = this.get_partner();

			if(this.pos.pos_loyalty_setting.length != 0)
			{	
			   if (this.pos.pos_loyalty_setting[0].loyalty_basis_on == 'pos_category') {
					if (partner_id){
						let loyalty = 0;
						for (let i = 0; i < orderlines.length; i++) {
							let lines = orderlines[i];
							let cat_ids = this.pos.db.get_category_by_id(lines.product.pos_categ_id[0])
							if(cat_ids){
								if (cat_ids['Minimum_amount']>0){
									final_loyalty += lines.get_price_with_tax() / cat_ids['Minimum_amount'];
								}
							}
						}
						return parseFloat(final_loyalty.toFixed(2));
					}
			   }else if (this.pos.pos_loyalty_setting[0].loyalty_basis_on == 'amount') {
					let loyalty_total = 0;
					if (order && partner_id){
						let amount_total = order.get_total_with_tax();
						let subtotal = order.get_total_without_tax();
						let loyaly_points = this.pos.pos_loyalty_setting[0].loyality_amount;
						final_loyalty += (amount_total / loyaly_points);
						
						loyalty_total = partner_id.loyalty_points1 + final_loyalty;
						return parseFloat(final_loyalty.toFixed(2));
					}
				}
			}
			let final_loyalty_value =parseFloat(final_loyalty.toFixed(2))
			order.set_loaylty_value(final_loyalty_value)
			return parseFloat(final_loyalty.toFixed(2));
		}

	}

	Registries.Model.extend(Order, PosOrder);

	const PaymentLine = (Payment) => class PaymentLine extends Payment {
        setup() {
            super.setup();
            this.pos_reference = this.pos_reference || "";
        }

        set_pos_reference(pos_reference){
            this.pos_reference = pos_reference;
        }

        get_pos_reference(){
            return this.pos_reference;
        }
        
        init_from_JSON(json){
            super.init_from_JSON(...arguments);
            this.pos_reference = json.pos_reference || "";
        }

        export_as_JSON(){
            const json = super.export_as_JSON(...arguments);
            json.pos_reference = this.pos_reference || "";
            return json;
        }

        export_for_printing() {
            const json = super.export_for_printing(...arguments);
            json.pos_reference = this.pos_reference || "";
            return json;
        }

    }
    Registries.Model.extend(Payment, PaymentLine);

})
