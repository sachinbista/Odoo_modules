odoo.define('pos_orders_all.TicketButton', function(require){
	'use strict';

	const TicketButton = require('point_of_sale.TicketButton');
    const Registries = require('point_of_sale.Registries');


   const BiTicketButton = TicketButton =>
	   	class extends TicketButton {
			setup() {
				super.setup();
			}
            onClick() {
                var self = this;
                var order = self.env.pos.get_order();
                if(order.is_partial){
                    alert("This is a partial order, so you cannot make a payment from here.");
                }
                else{
                    if (this.props.isTicketScreenShown) {
                        this.env.posbus.trigger('ticket-button-clicked');
                    } else {
                        this.showScreen('TicketScreen');
                    }
                }
            }
            
	   	};
   Registries.Component.extend(TicketButton, BiTicketButton);

   return TicketButton;

});