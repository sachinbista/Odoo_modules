odoo.define('bista_website_image_360.script_product', function (require) {
    "use strict";

    require('website_sale.website_sale');
    var publicWidget = require('web.public.widget');
    publicWidget.registry.WebsiteSale.include({
        events: _.extend({}, publicWidget.registry.WebsiteSale.prototype.events, {
            'mousemove .modal-content': 'update_product_image',
        }),
        update_product_image: function (event) {
            var pic_W = $('.modal-content').width();
            var mouse_X = event.pageX - (pic_W / 2);
            var total_img_count = $('.list li').length + 1;
            if (total_img_count <= 0) {
                total_img_count = 1;
            }
            var interval_screen = pic_W / total_img_count;
            var interval = mouse_X / interval_screen;
            var index = Math.abs(Math.round(interval));
            $('.list li').eq(index).show().siblings().hide();
        },
    });
});
