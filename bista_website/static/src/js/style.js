odoo.define('bista_website.style', function (require) {
    'use strict';

    const publicWidget = require('web.public.widget');
    const {_t} = require('web.core');
    const ajax = require('web.ajax');
    
    publicWidget.registry.CopyLinkButton = publicWidget.Widget.extend({
        selector: '.o_clipboard_button.o_btn_char_copy',
        events: {
            click: '_onClick'
        },
        async _onClick(event) {
            event.preventDefault();
            let url = document.location.href;
            var self = this;
            $(self.el).tooltip({title: _t("Copied !"), trigger: "manual", placement: "bottom"});
            var clipboard = new ClipboardJS('.o_clipboard_button', {
                text: function () {
                    return url;
                },
                container: self.el
            });
            clipboard.on('success', function () {
                clipboard.destroy();
                $(self.el).tooltip('show');
                _.delay(function () {
                    $(self.el).tooltip("hide");
                }, 800);
            });
            clipboard.on('error', function (e) {
                clipboard.destroy();
            });
        }
    });

    publicWidget.registry.AddGiftCard = publicWidget.Widget.extend({
        selector: '.oe_website_sale',
        events: {
            'click .action_add_gift_card': '_onAddGiftCardProduct',
            'click .gc_action_edit': '_onActionEdit',
        },
        _onActionEdit: function (ev) {
            var gift_tr = $(ev.currentTarget).parents('.gift_card_tr')
            gift_tr.find("#gift_card_message").removeClass('gift_input_readonly');
            gift_tr.find(".save_gift_card").removeClass('d-none');
            $(ev.currentTarget).addClass("d-none");
        },
        _onAddGiftCardProduct: function (ev) {
            var gift_message_text = false
            var gift_message_text = $(ev.currentTarget).parents('.gift_card_tr').find('textarea[name = gift_card_message]').val();
            if(gift_message_text.length == 0){
                if(!$('.gift_msg_empty_warning').length){
                    $(".gift_card_action_btn_div").before("<span class='text-danger gift_msg_empty_warning'>Please add your message</span>")
                }
            }else{
                $('.gift_msg_empty_warning').remove();
                var is_update = 0
                if($(ev.currentTarget).hasClass("save_gift_card")){
                    is_update = 1
                }
                ajax.jsonRpc('/add/gift/message/product', 'call', {'gift_message': $.trim(gift_message_text),'is_update':is_update}).then(function (data) {
                    window.location.href = '/shop/cart';
                })
            }
        },
    });
});
