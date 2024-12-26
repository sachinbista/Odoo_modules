odoo.define('bista_product_engraving.website_sale', function (require) {
    'use strict';

    var publicWidget = require('web.public.widget');
    require('website_sale.website_sale');
    publicWidget.registry.WebsiteSale.include({

        /**
         * Overridden to r
         *
         * @override
         */
        _submitForm() {
            const $product_engrave = $('#product_detail #engrave-content');
            var engrave_msg = '';
            var engrave_font = '';
            if($product_engrave.length) {
                engrave_msg = $product_engrave.find('input[name="engrave_msg"]').val();
                engrave_font = $product_engrave.find('input[name="selectedfontstyle"]').val();
            }
            this.rootProduct['engrave_msg'] = engrave_msg;
            this.rootProduct['engrave_font'] = engrave_font;
            var ret = this._super(...arguments);
            ret.then(()=>{
                this.rootProduct['engrave_msg'] = '';
                this.rootProduct['engrave_font'] = '';
            });
            return ret;
        },
    });
});