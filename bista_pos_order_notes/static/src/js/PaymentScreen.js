odoo.define('bista_pos_order_notes.PosordernotePaymentScreen', function(require) {
    
    const PaymentScreen = require('point_of_sale.PaymentScreen');
    const Registries = require('point_of_sale.Registries');
    const { useListener } = require("@web/core/utils/hooks");
    const {onMounted} = owl;
    const PosordernotePaymentScreen = PaymentScreen => class extends PaymentScreen {

        setup() {
            super.setup();
        }
        onChangeTextNote(ev){
          var $target = $(ev.currentTarget);
            this.env.pos.get_order().set_order_note($target.val())
            console.log(this);
        }

       }

    Registries.Component.extend(PaymentScreen, PosordernotePaymentScreen);
}); 
