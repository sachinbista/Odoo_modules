
odoo.define('pos_all_in_one.ProductTemplatePopupWidget', function(require){
	'use strict';

	const Popup = require('point_of_sale.ConfirmPopup');
	const Registries = require('point_of_sale.Registries');
    const { useListener } = require("@web/core/utils/hooks");	

	class ProductTemplatePopupWidget extends Popup {

		setup() {
            super.setup();
            useListener('click-product-template', this.add_product_variant);
        }

        add_product_variant(ev){
            if(this.env.pos.config.allow_selected_close == "auto_close"){
                this.env.pos.get_order().add_product(ev.detail);
                this.env.posbus.trigger('close-popup', {
                    popupId: this.props.id,
                    response: { confirmed: false, payload: null },
                });
            }else if(this.env.pos.config.allow_selected_close == "selected"){
                this.env.pos.get_order().add_product(ev.detail);
            }
        }
	}
	
	ProductTemplatePopupWidget.template = 'ProductTemplatePopupWidget';

	Registries.Component.add(ProductTemplatePopupWidget);

	return ProductTemplatePopupWidget;

});