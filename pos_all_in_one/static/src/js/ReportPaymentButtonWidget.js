odoo.define('pos_all_in_one.ReportPaymentButtonWidget', function(require) {
    'use strict';

    const PosComponent = require('point_of_sale.PosComponent');
    const ProductScreen = require('point_of_sale.ProductScreen');
    const { useListener } = require("@web/core/utils/hooks");
    const Registries = require('point_of_sale.Registries');

    class ReportPaymentButtonWidget extends PosComponent {
        setup() {
            super.setup();
            // useListener('click-product-template', this.add_product_variant);
            useListener('click', this.onClick);
        }

        async onClick(){
            var self = this;
            self.showPopup('PopupPaymentWidget',{
                'title': 'Payment Summary',
            });
        }

        
    }
    
    ReportPaymentButtonWidget.template = 'ReportPaymentButtonWidget';
    ProductScreen.addControlButton({
        component: ReportPaymentButtonWidget,
        condition: function() {
            return this.env.pos.config.payment_summery;
        },
    });
    Registries.Component.add(ReportPaymentButtonWidget);
    return ReportPaymentButtonWidget;
});