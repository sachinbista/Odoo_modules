
odoo.define('pos_all_in_one.ReportLocationButtonWidget', function(require) {
    'use strict';

    const PosComponent = require('point_of_sale.PosComponent');
    const ProductScreen = require('point_of_sale.ProductScreen');
    const { useListener } = require("@web/core/utils/hooks");
    let core = require('web.core');
    let _t = core._t;
    const Registries = require('point_of_sale.Registries');


    class ReportLocationButtonWidget extends PosComponent {
        setup() {
            super.setup();
            useListener('click', this.onClick);
        }
            
        async onClick(){
            var self = this;
            self.showPopup('PopupLocationWidget',{
                'title': 'Audit Report',
            });
        }
    }

    ReportLocationButtonWidget.template = 'ReportLocationButtonWidget';
    ProductScreen.addControlButton({
        component: ReportLocationButtonWidget,
        condition: function() {
            return this.env.pos.config.loc_summery;
        },
    });
    Registries.Component.add(ReportLocationButtonWidget);
    return ReportLocationButtonWidget;
});