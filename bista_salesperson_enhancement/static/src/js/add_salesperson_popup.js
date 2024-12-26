odoo.define('bista_salesperson_enhancement.AdditionalSalespersonPopup', function (require) {
    'use strict';

    const AbstractAwaitablePopup = require('point_of_sale.AbstractAwaitablePopup');
    const Registries = require('point_of_sale.Registries');
    const { _lt } = require('@web/core/l10n/translation');

    const { useState } = owl;

     class AdditionalSalespersonPopup extends AbstractAwaitablePopup {
         setup() {
            super.setup();
            this.state = useState({ selectedId: this.props.list.find((item) => item.isSelected) });

        }
        selectItem(itemId) {
            this.state.selectedId = itemId;
            this.confirm();
        }
        getPayload(params) {
            const $orderSalespersonCheckboxes = this.el.querySelectorAll("input[type='checkbox'][name='flexCheckChecked']:checked");
            var other_users = Array.from($orderSalespersonCheckboxes).map((checkbox) => {
                const id = checkbox.value;
                const labelElement = checkbox.nextElementSibling;
                const label = labelElement.textContent.trim();
                return { id, label };
            });


        }
     }
    AdditionalSalespersonPopup.template = 'AdditionalSalespersonPopup';
    AdditionalSalespersonPopup.defaultProps = {
        confirmText: _lt('Confirm'),
        cancelText: _lt('Cancel'),
        title: _lt('Sales Person'),
        body: '',
        list: [],
        confirmKey: false,
    };

    Registries.Component.add(AdditionalSalespersonPopup);

    return AdditionalSalespersonPopup
});