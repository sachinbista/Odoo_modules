
odoo.define('pos_orders_all.CouponPrint', function(require) {
	'use strict';

	const PosComponent = require('point_of_sale.PosComponent');
	const Registries = require('point_of_sale.Registries');
    const {onMounted} = owl;

	class CouponPrint extends PosComponent {
		setup() {
			super.setup();
			var self = this;
			var order = this.env.pos.get_order();
			var number_bar = this.props.data.coup_code;

			onMounted(() => {
				$("#barcode_print2").barcode(
					number_bar, // Value barcode (dependent on the type of barcode)
					"code128" // type (string)
				);
            });
			
		}


		coupon_render_env() {
			var data= this.props.data;
			var vals = {
				widget: this,
				pos: this.env.pos,
				name: data.coup_name,
				issue: data.coup_issue_dt,
				expire : data.coup_exp_dt,
				amount : data.coup_amount,
				number : data.coup_code,
				am_type : data.am_type,
			}
			return vals;
		}
	}
	
	CouponPrint.template = 'CouponPrint';
	Registries.Component.add(CouponPrint);
	return CouponPrint;
});