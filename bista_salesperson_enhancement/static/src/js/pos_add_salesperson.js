odoo.define('bista_salesperson_enhancement.pos_add_salesperson', function(require) {
    'use strict';

    const PosComponent = require('point_of_sale.PosComponent');
    const ProductScreen = require('point_of_sale.ProductScreen');
    const { useListener } = require('@web/core/utils/hooks');
    const Registries = require('point_of_sale.Registries');

    class AdditonalSalesperson extends PosComponent {
        setup() {
            super.setup();
            useListener('click', this.onClick);
        }
        async onClick() {
            var SelectedSP = []
            var addlabel = [];
            var array_list = []

            const selectedOrderline = this.env.pos.get_order().get_selected_orderline();
            const order = this.env.pos.get_order();
            if (!selectedOrderline) return;

            var self = this;
            var result = await this.rpc({
                   model: 'res.users',
                   method: 'search_read',
                   fields:['name'],
            });
            result.sort((a, b) => a.name.localeCompare(b.name));

            if (order.get_sales_person() != null){
                order.get_sales_person().forEach (element=> array_list.push(Number(element)));
            }
            for (let i=0; i<result.length;i++){
                if(array_list.includes(result[i].id))
                {
                    result[i].is_selected= true
                }
            }
            const { confirmed,payload:users } = await this.showPopup('AdditionalSalespersonPopup', {
                title: this.env._t('Add Other SP'),
                list: result
            });

            if (confirmed) {
                    $("input:checkbox[name=flexCheckChecked]:checked").each(function(){
                    const id = $(this).val();
                    const label = $(this).next().text().trim();
                    SelectedSP.push(id);
                    addlabel.push( label );
                    });
                var combinedLabels = addlabel.join(', ');

                var other_selected_users = SelectedSP;
                var pos_order = this.env.pos.get_order();
                var final_other_users = [];
                for(var i = 0; i < other_selected_users.length; i++){
                    final_other_users.push(other_selected_users[i])
                }
                pos_order.other_users = final_other_users ;
                pos_order.set_sales_person(final_other_users);
                pos_order.set_sales_person_names(combinedLabels);
                }
            }
    }
    AdditonalSalesperson.template = 'AdditonalSalesperson';

    ProductScreen.addControlButton({
        component: AdditonalSalesperson,
    });

    Registries.Component.add(AdditonalSalesperson);

    return AdditonalSalesperson;
});

