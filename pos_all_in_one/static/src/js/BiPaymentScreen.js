odoo.define('pos_all_in_one.BiPaymentScreen', function(require) {

	const PaymentScreen = require('point_of_sale.PaymentScreen');
    const Registries = require('point_of_sale.Registries');
    const { useListener } = require("@web/core/utils/hooks");
    const {onMounted} = owl;

	const BiPaymentScreen = PaymentScreen => class extends PaymentScreen {

		setup() {
			super.setup();
			this.mobile_multi = false
			useListener('click-update_amount', this._UpdateAmountt);
			useListener('click-cur-switch', this._UpdateDetails);
			useListener('click-cur-switch-mobile', this._UpdateDetailsMobile);

			onMounted(() => {
               	$('#details_mobile').hide()
				// $('#details').hide()
            });

		}

		_UpdateDetails() {
			if($("#cur-switch").prop('checked') == true){
				$('#details').hide()
			}
			else{
				$('#details').show()
			}
		}

		_UpdateDetailsMobile() {
			$(".js_multi").toggleClass("highlight");
			if(this.mobile_multi == true){
				$('#details_mobile').hide()
				
				this.mobile_multi = false
			}else{
				$('#details_mobile').show()
				this.mobile_multi = true
			}
		}

		get check_mobile_multi(){
			return this.mobile_multi;
		}

		async selectClient() {
			let order = this.env.pos.get_order();
			let self = this;
			if(order.redeem_done){
				this.showPopup('ErrorPopup',{
					'title': this.env._t('Cannot Change Customer'),
					'body': this.env._t('Sorry, you redeemed product, please remove it before changing customer.'),
				}); 
			}else{
				const currentPartner = this.currentOrder.get_partner();
				const { confirmed, payload: newClient } = await this.showTempScreen(
					'PartnerListScreen',
					{ partner: currentPartner }
				);
				if (confirmed) {
					this.currentOrder.set_partner(newClient);
					this.currentOrder.updatePricelist(newClient);
				}
			}
		}

		get multiCurrency(){
			let currency = this.env.pos.poscurrency;

			var selected_curr = this.env.pos.config.selected_currency
			var selected_curr_list = []

			for (var i in selected_curr){
				selected_curr_list.push(selected_curr[i])
			}

			let final_currency = []

			for (var curr in currency){
				if(selected_curr_list.includes(currency[curr].id)){
					final_currency.push(currency[curr])
				}
			}

			return final_currency
		}

		_UpdateAmountt() {
			let self = this;
			let order = this.env.pos.get_order();
			let paymentlines = this.env.pos.get_order().get_paymentlines();
			let open_paymentline = false;
			let tot = order.get_curamount();
			let tot_amount = 0;
			let currency = this.env.pos.poscurrency;
			let user_amt = $('.edit-amount').val();
			let cur = $('.drop-currency').val();
			let payment_methods_from_config = this.env.pos.payment_methods.filter(method => this.env.pos.config.payment_method_ids.includes(method.id));
			order.add_paymentline(payment_methods_from_config[0]);
			let selected_paymentline = order.selected_paymentline;
			for(var i=0;i<currency.length;i++){
				if(cur==currency[i].id){
					let c_rate = self.env.pos.currency.rate/currency[i].rate;
					tot_amount = parseFloat(user_amt)*c_rate;
					selected_paymentline.amount =parseFloat(tot_amount.toFixed(2));
					selected_paymentline.amount_currency =parseFloat(parseFloat(user_amt).toFixed(2)) ;
					$('.show-payment').text(this.env.pos.format_currency_no_symbol(selected_paymentline.amount));
					selected_paymentline.set_curname(currency[i].name);
					selected_paymentline.set_curamount(selected_paymentline.amount_currency);
					selected_paymentline.set_currency_symbol(currency[i].symbol);
				}
			}
			order.get_paymentlines();
			if (!order) {
				return;
			} else if (order.is_paid()) {
				$('.next').addClass('highlight');
			}else{
				$('.next').removeClass('highlight');
			}
			$('.edit-amount').val('');
			self._ChangeCurrency();
			window.document.body.removeEventListener('keypress', self.keyboard_handler);
			window.document.body.removeEventListener('keydown', self.keyboard_keydown_handler);
		}

		_ChangeCurrency() {
			let self = this;
			let currencies = this.env.pos.poscurrency;
			let cur = $('.drop-currency').val();
			let curr_sym;
			let order= this.env.pos.get_order();
			let pos_currency = this.env.pos.currency;
			for(var i=0;i<currencies.length;i++){
				if(cur != pos_currency.id && cur==currencies[i].id){
					let currency_in_pos = (currencies[i].rate/self.env.pos.currency.rate).toFixed(6);
					$('.currency_symbol').text(currencies[i].symbol);
					$('.currency_rate').text(currency_in_pos);
					curr_sym = currencies[i].symbol;

					let curr_tot =order.get_due()*currency_in_pos;
					$('.currency_cal').text(parseFloat(curr_tot.toFixed(6)));
					order.set_curamount(parseFloat(curr_tot.toFixed(6)));
					order.set_symbol(curr_sym);
					order.set_curname(currencies[i].name);
					return curr_tot;
				}
				if(cur == pos_currency.id && cur==currencies[i].id){
					$('.currency_symbol').text(pos_currency.symbol);
					$('.currency_rate').text(1);
					curr_sym = pos_currency.symbol;

					let curr_tot =order.get_due();
					$('.currency_cal').text(parseFloat(curr_tot.toFixed(2)));
					order.set_curamount(parseFloat(curr_tot.toFixed(2)));
					order.set_symbol(curr_sym);
					order.set_curname(pos_currency.name);
					return curr_tot;
				}
			}
		}
	}

	Registries.Component.extend(PaymentScreen, BiPaymentScreen);

	return PaymentScreen;
});