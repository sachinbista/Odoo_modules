
odoo.define('pos_all_in_one.ReportOrderButtonWidget', function(require) {
    'use strict';

    const PosComponent = require('point_of_sale.PosComponent');
    const ProductScreen = require('point_of_sale.ProductScreen');
    const { useListener } = require("@web/core/utils/hooks");
    const Registries = require('point_of_sale.Registries');

    class ReportOrderButtonWidget extends PosComponent {
        setup() {
            super.setup();
            useListener('click', this.onClick);
        }
            
        async onClick(){
            var self = this;
            self.showPopup('PopupOrderWidget',{
                'title': 'Payment Summary',
            });
        }
    }
    ReportOrderButtonWidget.template = 'ReportOrderButtonWidget';
    ProductScreen.addControlButton({
        component: ReportOrderButtonWidget,
        condition: function() {
            return this.env.pos.config.order_summery;
        },
    });
    Registries.Component.add(ReportOrderButtonWidget);
    return ReportOrderButtonWidget;
});