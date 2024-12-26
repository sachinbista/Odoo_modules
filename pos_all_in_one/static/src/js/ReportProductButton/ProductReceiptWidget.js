
odoo.define('pos_all_in_one.ProductReceiptWidget', function(require) {
    'use strict';

    const PosComponent = require('point_of_sale.PosComponent');
    const ReceiptScreen = require('point_of_sale.ReceiptScreen');
    const Registries = require('point_of_sale.Registries');
    const ProductScreen = require('point_of_sale.ProductScreen');
    

    const ProductReceiptWidget = (ReceiptScreen) => {
        class ProductReceiptWidget extends ReceiptScreen {
       		setup() {
				super.setup();
			}

        	back(){
				this.trigger('close-temp-screen');
				this.showScreen('ProductScreen');
			}

        	get_pro_summery(){
				return this['props']['output_summery_product'];
			}
		
			get_product_st_date(){
				return this['props']['pro_st_date'];
			}
			get_product_ed_date(){
				return this['props']['pro_ed_date'];
			}

			get product_receipt_data() {
				return {
					widget: this,
					pos: this.pos,
					prod_current_session : this['props']['prod_current_session'],
					p_summery: this.get_pro_summery(),
					p_st_date: this.get_product_st_date(),
					p_ed_date: this.get_product_ed_date(),
					date_p: (new Date()).toLocaleString(),
					langs:this.env.pos.langs,
				};
			}
		}
		ProductReceiptWidget.template = 'ProductReceiptWidget';
		return ProductReceiptWidget

    };
    

    Registries.Component.addByExtending(ProductReceiptWidget,ReceiptScreen);

    return ProductReceiptWidget;
});