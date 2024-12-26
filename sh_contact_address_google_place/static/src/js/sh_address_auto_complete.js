/** @odoo-module **/

import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";
import { CharField } from "@web/views/fields/char/char_field";
import { useInputField } from "@web/views/fields/input_field_hook";
import { Dialog } from "@web/core/dialog/dialog";
const { useRef, Component, onMounted } = owl;
import { useService } from "@web/core/utils/hooks";
import { qweb } from 'web.core';
import { debounce } from"@web/core/utils/timing";
import { markup, toRaw } from "@odoo/owl";

export class ShAddressAutoComplete extends CharField {

    /**
    * The purpose of this extension
    * is to allow initialize component
    * @override
    */
    setup() {
        super.setup();
        this.inputRef = useRef("input");
        this.rpc = useService("rpc");
        useInputField({ getValue: () => this.props.value || "", parse: (v) => this.parse(v), ref: this.inputRef });
        this.onInputEventAddress = debounce(this.onInputEventAddress, 200);
        this.dialogService = useService("dialog");
    }

    _hideAddressesDropdown($container) {
        const addressDropdown = $container.find('.js_cls_address_dropdown');
        if (addressDropdown) {
            addressDropdown.remove();
        }
    }

    async _renderAddressDropdown() {
        var self = this;
        if (self.inputRef.el.value) {
            const results = await self.rpc("/sh_contact_address_google_place/partial_address", { partial_address: self.inputRef.el.value });
            if (results.length) {
                var data = qweb.render("sh_contact_address_google_place.AddressDropDown", {
                    results: results
                })
                if (data) {
                    self.addressDropdown = $(data).length ? $(data)[0] : false;
                    return self.addressDropdown;
                }
            }
        }
        if (self.inputRef.el.parentNode) {
            self._hideAddressesDropdown($(self.inputRef.el.parentNode));
        }
    }

    async onInputEventAddress() {
        var self = this;
        await self._renderAddressDropdown().then(async function (response) {
            if (response) {
                const inputC = self.inputRef.el.parentNode;
                if (inputC) {
                    self._hideAddressesDropdown($(inputC));
                    await inputC.appendChild(response);
                    const addressDropdownItem = $(inputC).find('.js_cls_address_dropdown > .js_cls_address_result_item');
                    if (addressDropdownItem.length) {
                        addressDropdownItem.on('click', self.onClickDropdownItem.bind(self))
                    }
                }
            }
        });
    }

    async onClickDropdownItem(ev) {
        var self = this;
        this.inputRef.el.value = this.googleText = ev.currentTarget.innerText;
        const addressDropdownItem = self.inputRef.el.parentNode;
        const $addressContainer = $(addressDropdownItem.parentNode);
        self._hideAddressesDropdown($addressContainer);
        this.results = await self.rpc("/sh_contact_address_google_place/fill_address", { address: self.inputRef.el.value || ev.currentTarget.innerText, place_id: ev.currentTarget.dataset.placeId });
        this.results.customer_rank = this.env.model.root.data.customer_rank;
        if (this.results) {
            this.validAddress = await this.validateAddress(this.results);
            if(this.validAddress) {
                const dialogProps = {
                    address: this.results,
                    validAddress: this.validAddress,
                    onSaveAddress: this.onSaveAddress.bind(this),
                };
                this.dialogService.add(ValidatorDialog, dialogProps);

            } else {
                await this.onSaveAddress('no');
            }
        }
    }
    async validateAddress(results) {
        return await this.rpc(
            '/validate/address',
            {
                address: results,
            }
        );
    }
    async onSaveAddress(option) {
        // -------------------------------------
        // Write value in input and Trigger Input Change
        // -------------------------------------
        var address =  option === 'yes' ? this.validAddress : this.results
        let addressEl = false
        let $model_body = $('.modal-content:not(.o_validation_dialog').find('.modal-body');
        if ($model_body.length) {
            addressEl = $('.modal-body').find('[id="sh_contact_place_text"]')[0]
        } else {
            addressEl = document.getElementById("sh_contact_place_text");
        }
        if (addressEl) {
            addressEl.value = ''
            addressEl.value = JSON.stringify(address);
            addressEl.dispatchEvent(new InputEvent("input", {bubbles: true}));
            addressEl.dispatchEvent(new InputEvent("enter", {bubbles: true}));
            addressEl.dispatchEvent(new InputEvent("change", {bubbles: true}));
        }
        // -------------------------------------
        // Write value in input and Trigger Input Change
        // -------------------------------------

        // -------------------------------------
        // Write value in input and Trigger Input Change
        // -------------------------------------
        addressEl = false
        if ($model_body.length) {
            addressEl = $('.modal-body').find('[id="sh_contact_place_text_main_string"]')[0]
        } else {
            addressEl = document.getElementById("sh_contact_place_text_main_string");
        }
        if (addressEl) {
            addressEl.value = '';
            addressEl.dispatchEvent(new InputEvent("input", {bubbles: true}));
            addressEl.dispatchEvent(new InputEvent("enter", {bubbles: true}));
            addressEl.dispatchEvent(new InputEvent("change", {bubbles: true}));
            addressEl.value = this.googleText.trim();
            addressEl.dispatchEvent(new InputEvent("input", {bubbles: true}));
            addressEl.dispatchEvent(new InputEvent("enter", {bubbles: true}));
            addressEl.dispatchEvent(new InputEvent("change", {bubbles: true}));
        }
    }
}

ShAddressAutoComplete.template = "sh_contact_address_google_place.CharField";
registry.category("fields").add("sh_address_auto_complete", ShAddressAutoComplete);

export class ValidatorDialog extends Component {
    setup() {
        this.title = this.env._t("Validate Address");
    }
    saveAddress(ev) {
        ev.stopPropagation();
    	ev.preventDefault();
    	let option = $("input[name='address_validation']:checked").val() || 'no';
        this.props.onSaveAddress(option);
        this.props.close();
    }

}

ValidatorDialog.props = {
    close: { type: Function },
    onSaveAddress: { type: Function },
    address: { type: Object },
    validAddress: { type: Object },
};

ValidatorDialog.template = "address_validation.ValidatorDialog";
ValidatorDialog.components = { Dialog };
