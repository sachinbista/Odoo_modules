
odoo.define('pos_all_in_one.ReportCategoryButtonWidget', function(require) {
    'use strict';

    const PosComponent = require('point_of_sale.PosComponent');
    const ProductScreen = require('point_of_sale.ProductScreen');
    const { useListener } = require("@web/core/utils/hooks");
    const Registries = require('point_of_sale.Registries');


    class ReportCategoryButtonWidget extends PosComponent {
        setup() {
            super.setup();
            useListener('click', this.onClick);
        }
            
        async onClick(){
            var self = this;
            self.showPopup('PopupCategoryWidget',{
                'title': 'Payment Summary',
            });
        }
    }


    ReportCategoryButtonWidget.template = 'ReportCategoryButtonWidget';
    ProductScreen.addControlButton({
        component: ReportCategoryButtonWidget,
        condition: function() {
            return this.env.pos.config.product_categ_summery;
        },
    });
    Registries.Component.add(ReportCategoryButtonWidget);
    return ReportCategoryButtonWidget;
});