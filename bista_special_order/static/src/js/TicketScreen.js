odoo.define('bista_special_order.TicketScreen', function (require) {
    'use strict';

    const { Order } = require('point_of_sale.models');
    const Registries = require('point_of_sale.Registries');
    const TicketScreen = require('point_of_sale.TicketScreen');
    const NumberBuffer = require('point_of_sale.NumberBuffer');
    const { useListener } = require("@web/core/utils/hooks");
    const { parse } = require('web.field_utils');
    const { _lt } = require('@web/core/l10n/translation');



    const { onMounted, onWillUnmount, useState } = owl;

    const PosTicketScreenInherit = (TicketScreen) => class PosTicketScreenInherit extends TicketScreen{

        _onUpdateSelectedOrderline({ detail }) {
            const buffer = detail.buffer;
            const order = this.getSelectedSyncedOrder();
            if (!order) return NumberBuffer.reset();

            const selectedOrderlineId = this.getSelectedOrderlineId();
            const special_product_refund =  this.env.pos.config.bs_special_refund;
            const orderline = order.orderlines.find((line) => line.id == selectedOrderlineId);
            if (!orderline) return NumberBuffer.reset();

            if(orderline.is_special && special_product_refund == false){
                this.showPopup('ErrorPopup', {
                        title: this.env._t('Special Order'),
                        body: _.str.sprintf(
                            this.env._t(
                                "You can't refund/return the Special/Customized Items!"
                            ),
                        ),
                    });
                return;
            }
            const toRefundDetail = this._getToRefundDetail(orderline);
            // When already linked to an order, do not modify the to refund quantity.
            if (toRefundDetail.destinationOrderUid) return NumberBuffer.reset();

            const refundableQty = toRefundDetail.orderline.qty - toRefundDetail.orderline.refundedQty;
            if (refundableQty <= 0) return NumberBuffer.reset();

            if (buffer == null || buffer == '') {
                toRefundDetail.qty = 0;
            } else {
                const quantity = Math.abs(parse.float(buffer));
                if (quantity > refundableQty) {
                    NumberBuffer.reset();
                    this.showPopup('ErrorPopup', {
                        title: this.env._t('Maximum Exceeded'),
                        body: _.str.sprintf(
                            this.env._t(
                                'The requested quantity to be refunded is higher than the ordered quantity. %s is requested while only %s can be refunded.'
                            ),
                            quantity,
                            refundableQty
                        ),
                    });
                } else {
                    toRefundDetail.qty = quantity;
                }
            }
        }
        _prepareAutoRefundOnOrder(order) {
            const selectedOrderlineId = this.getSelectedOrderlineId();
            const orderline = order.orderlines.find((line) => line.id == selectedOrderlineId);
            if (!orderline || orderline.is_special) return false;

            const toRefundDetail = this._getToRefundDetail(orderline);
            const refundableQty = orderline.get_quantity() - orderline.refunded_qty;
            if (this.env.pos.isProductQtyZero(refundableQty - 1) && toRefundDetail.qty === 0) {
                toRefundDetail.qty = 1;
            }
            return true;
        }
   }

   Registries.Component.extend(TicketScreen,PosTicketScreenInherit);
});
