odoo.define('bista_pos_traceability.pos_models', function (require) {
"use strict";
    const EditListPopup = require('point_of_sale.EditListPopup');
    const Registries = require('point_of_sale.Registries');
    var rpc = require('web.rpc');

    const PosEditlistpopup = (EditListPopup) =>
        class extends EditListPopup {
             async confirm() {
                 var order = this.env.pos.get_order();
                 var product = order && order.lot_product && order.lot_product.id
                 if (this.props.title == 'Lot/Serial Number(s) Required'){

                         var lot_string = this.state.array
                         var lot_names = [];
                         for (var i = 0; i < lot_string.length; i++) {

                            if (lot_string[i].text != ""){
                                lot_names.push(lot_string[i].text);
                            }

                         }

                         const result =  await rpc.query({
                                                model: 'serial_no.validation',
                                                method: 'validate_lots',
                                                args: [lot_names,product]
                                                })

                            if(result != true){
                                if(result[0] == 'no_stock'){
                                    this.showPopup('ErrorPopup', {
                                        'title': this.env._t('Insufficient stock'),
                                        'body': this.env._t("Insufficient stock for " + result[1]),
                                    });

                                }

                                else if(result[0] == 'duplicate'){
                                    this.showPopup('ErrorPopup', {
                                        'title': this.env._t('Duplicate entry'),
                                        'body': this.env._t("Not Allowing Duplicate Serial Number " + result[1]),
                                    });
                                }
                                else if(result[0] == 'except'){
                                    alert("Exception occured with " + result[1])
                                    this.showPopup('ErrorPopup', {
                                        'title': this.env._t('Exception'),
                                        'body': this.env._t("Exception occured with" + result[1]),
                                    });
                                }
                            }
                            else{

                             this.env.posbus.trigger('close-popup', {
                                popupId: this.props.id,
                                response: { confirmed: true, payload: await this.getPayload() },
                            });


                            }
                 }
                 else{
                         this.env.posbus.trigger('close-popup', {
                                popupId: this.props.id,
                                response: { confirmed: true, payload: await this.getPayload() },
                            });

                 }

            }

        };

    Registries.Component.extend(EditListPopup, PosEditlistpopup);

    return EditListPopup;


});



