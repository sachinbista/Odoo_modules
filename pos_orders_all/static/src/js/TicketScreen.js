odoo.define('pos_orders_all.TicketScreen', function(require){
	'use strict';

	const TicketScreen = require('point_of_sale.TicketScreen');
    const Registries = require('point_of_sale.Registries');
    const NumberBuffer = require('point_of_sale.NumberBuffer');
``


   const BiTicketScreen = TicketScreen =>
	   	class extends TicketScreen {
			setup() {
				super.setup();
			}
            _onClickOrder({ detail: clickedOrder }) {
                if (!clickedOrder || clickedOrder.locked) {
                    if (this._state.ui.selectedSyncedOrderId == clickedOrder.backendId) {
                        this._state.ui.selectedSyncedOrderId = null;
                    } else {
                        this._state.ui.selectedSyncedOrderId = clickedOrder.backendId;
                    }
                    if (!this.getSelectedOrderlineId()) {
                        // Automatically select the first orderline of the selected order.
                        const firstLine = clickedOrder.get_orderlines()[0];
                        if (firstLine) {
                            this._state.ui.selectedOrderlineIds[clickedOrder.backendId] = firstLine.id;
                        }
                    }
                    NumberBuffer.reset();
                } else {
                    if(clickedOrder.is_partial){
                        alert("This is a partial order, so you cannot make a payment from here.");
                        this.env.pos.add_new_order();
                        this.showScreen('ProductScreen');
                    }
                    else{
                        this._setOrder(clickedOrder);
                    }
                }
            }
            
	   	};
   Registries.Component.extend(TicketScreen, BiTicketScreen);

   return TicketScreen;

});