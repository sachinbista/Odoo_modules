
odoo.define('pos_orders_all.CouponReceiptScreen', function(require) {
	'use strict';

	const ReceiptScreen = require('point_of_sale.ReceiptScreen');
	const Registries = require('point_of_sale.Registries');
	const { useRef } = owl;

	const CouponReceiptScreen = (ReceiptScreen) => {
		class CouponReceiptScreen extends ReceiptScreen {
			setup() {
                super.setup();
				this.orderReceipt = useRef('order-receipt');
			}

			back() {
	            this.trigger('close-temp-screen');
	        }

			async handleAutoPrint() {
				if (this._shouldAutoPrint()) {
					const isPrinted = await this._printReceipt();
					if (isPrinted) {
						const { name, props } = this.nextScreen;
						this.showScreen(name, props);
					}
				}
			}

			orderDone() {
				const { name, props } = this.nextScreen;
				this.showScreen(name, props);
			}
		}
		CouponReceiptScreen.template = 'CouponReceiptScreen';
		return CouponReceiptScreen;
	};

	Registries.Component.addByExtending(CouponReceiptScreen, ReceiptScreen);
	return CouponReceiptScreen;
});