/* Copyright (c) 2016-Present Webkul Software Pvt. Ltd. (<https://webkul.com/>) */
/* See LICENSE file for full copyright and licensing details. */
/* License URL : <https://store.webkul.com/license.html/> */
odoo.define('pos_signature.pos_signature', function (require) {
    "use strict";
    const ReceiptScreen = require('point_of_sale.ReceiptScreen');
    const PaymentScreen = require('point_of_sale.PaymentScreen');
    const AbstractAwaitablePopup = require('point_of_sale.AbstractAwaitablePopup');
    const Registries = require('point_of_sale.Registries');
    const {useListener} = require("@web/core/utils/hooks");
    var {Order} = require('point_of_sale.models');
    // var SuperOrder = pos_model.Order;

    const PosOrder = (Order) => class extends Order {
        initialize(attributes, options) {
            this.signature_base64 = '';
            this.clicking = false;
            this.mouse = {x: 0, y: 0};
            this.canvas;
            this.ctx;
            // Order.prototype.initialize.call(this, attributes, options);
        }

        export_as_JSON() {
            var self = this;
            var loaded = super.export_as_JSON(...arguments);
            if (self.pos.get_order() != null) loaded.customer_signature = self.pos.get_order().signature_base64;
            return loaded;
        }
    };
    Registries.Model.extend(Order, PosOrder);
    // Inherit ReceiptScreen--------------
    const PosResReceiptScreen = (ReceiptScreen) => class extends ReceiptScreen {
        constructor() {
            super(...arguments);

            var self = this;
            setTimeout(function () {
                if (self.env.pos.get_order().signature_base64 === undefined) {
                    $("#customer_signature_table").hide();
                } else {
                    var signature_base64 = "data:image/png;base64," + self.env.pos.get_order().signature_base64;
                    var canvas = document.getElementById("receipt_sign");
                    var ctx = canvas.getContext("2d");
                    var image = new Image();
                    image.onload = function () {
                        canvas.width = parseInt(image.width);
                        canvas.height = parseInt(image.height);
                        ctx.drawImage(image, 0, 0);
                    };
                    image.src = signature_base64;
                }
            }, 200);
        }
    };
    Registries.Component.extend(ReceiptScreen, PosResReceiptScreen);

    // Signature Popup--------------
    class SignaturePopupWidget extends AbstractAwaitablePopup {
        setup() {
            super.setup();

            useListener('mousedown', '#paint', this.signature_mouse_down);
            useListener('touchstart', '#paint', this.signature_mouse_down);
            useListener('pointermove', '#paint', this.signature_mouse_move);
            useListener('touchmove', '#paint', this.signature_mouse_move);
            useListener('mouseup', '#paint', this.signature_mouse_up);
            useListener('touchend', '#paint', this.signature_mouse_up);

            var self = this;
            setTimeout(function () {
                var current_order = self.env.pos.get_order()
                current_order.signature_canvas = document.querySelector('#paint');
                current_order.ctx = current_order.signature_canvas.getContext('2d');
                if (current_order.signature_canvas) $('#sketch').html(current_order.signature_canvas);
            }, 1000);
        }

        clear_signature(event) {
            var current_order = this.env.pos.get_order();
            current_order.ctx.clearRect(0, 0, parseInt(current_order.signature_canvas.width), parseInt(current_order.signature_canvas.height));
            current_order.is_signature_draw = false;
            current_order.signature_base64 = '';
        }

        click_confirm(event) {
            var current_order = this.env.pos.get_order();
            if (current_order && current_order.is_signature_draw) {
                current_order.signature_base64 = current_order.signature_canvas.toDataURL("image/png").replace('data:image/png;base64,', "");
                current_order.signature_canvas = current_order.signature_canvas;
            }
            this.cancel();
        }

        signature_mouse_down(event) {
            this.env.pos.get_order().ctx.beginPath();
            this.env.pos.get_order().clicking = true;
        }

        signature_mouse_move(event) {
            var current_order = this.env.pos.get_order();
            current_order.signature_canvas = document.querySelector('#paint');
            current_order.ctx = current_order.signature_canvas.getContext('2d');
            var offset_left = $('#paint').offset().left;
            var offset_top = $('#paint').offset().top;
            var pageX = event.pageX ? event.pageX : event.originalEvent.touches[0].pageX
            var pageY = event.pageY ? event.pageY : event.originalEvent.touches[0].pageY
            current_order.ctx.x = Math.round(pageX - offset_left);
            current_order.ctx.y = Math.round(pageY - offset_top);
            current_order.ctx.lineWidth = 3;
            current_order.ctx.lineJoin = 'round';
            current_order.ctx.lineCap = 'round';
            current_order.ctx.strokeStyle = 'grey';
            if (current_order.clicking) {
                current_order.is_signature_draw = true;
                current_order.ctx.lineTo(current_order.ctx.x, current_order.ctx.y);
                current_order.ctx.stroke();
            }
        }

        signature_mouse_up(event) {
            this.env.pos.get_order().clicking = false;
        }
    }

    SignaturePopupWidget.template = 'SignaturePopupWidget';
    Registries.Component.add(SignaturePopupWidget);

    // Inherit PaymentScreen----------------
    const PosResPaymentScreen = (PaymentScreen_) => class extends PaymentScreen_ {
        add_signature(event) {
            this.showPopup('SignaturePopupWidget')
        }
    };
    Registries.Component.extend(PaymentScreen, PosResPaymentScreen);

});