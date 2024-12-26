odoo.define('website_configuration.brand_family_clear_filter', function (require) {
    "use strict";
    var ajax = require('web.ajax');
    var core = require('web.core');
    var utils = require('web.utils');
    var _t = core._t;

    var publicWidget = require('web.public.widget');
    require('website_sale.website_sale');

    publicWidget.registry.WebsiteSale.include({
        events: Object.assign({},   publicWidget.registry.WebsiteSale.prototype.events, {
            'click .brand_family_clear_filter': '_onClickClearBrandFilter',
            'click .brand_desc_read_more': '_onClickReadMoreBrandDescription',
        }),

        init: function () {
            var res = this._super.apply(this, arguments);
            var brand_desc_height = $(".brand_description").height();
            var brand_desc_height_p = $(".brand_description p").height();
            if(brand_desc_height < brand_desc_height_p){
                $(".brand_desc_read_more").removeClass("d-none");
            }else{
                $(".brand_desc_read_more").addClass("d-none");
            }
            return res
        },

        _onClickClearBrandFilter: function (ev) {
            var brand_f_id = $(ev.currentTarget).find('.brand_f_id').attr('id');
            var arrNumber = $("#brand_family_ids").val();
            arrNumber = arrNumber.split(",");
            arrNumber = $.grep(arrNumber, function(n) {
              return n != brand_f_id;
            });
            $("#brand_family_ids").attr("value",arrNumber)
            this.$("form.js_attributes").submit();
        },

        _onClickReadMoreBrandDescription: function (ev) {
            $(".brand_description").removeClass("brand_less_description").addClass("brand_full_description");
            $(".brand_desc_read_more").addClass("d-none");
        },
    })
})


