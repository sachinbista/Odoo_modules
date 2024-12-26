/** @odoo-module */
/* global Eway */

import { _t } from '@web/core/l10n/translation';
import paymentForm from '@payment/js/payment_form';
import { RPCError } from '@web/core/network/rpc_service';

paymentForm.include({
    /**
     * Return all relevant inline form inputs based on the payment method type of the provider.
     *
     * @private
     * @param {number} providerId - The id of the selected provider
     * @return {Object} - An object mapping the name of inline form inputs to their DOM element
     */
    _getEwayInlineFormInputs: function (providerId) {
        return {
            card: document.getElementById(`o_eway_card_${providerId}`),
            name_on_card: document.getElementById(`o_eway_name_on_card_${providerId}`),
            month: document.getElementById(`o_eway_month_${providerId}`),
            year: document.getElementById(`o_eway_year_${providerId}`),
            code: document.getElementById(`o_eway_code_${providerId}`),
        };
    },

    /**
         * Redirect the customer to Eway hosted payment page.
         *
         * @override method from payment.payment_form_mixin
         * @private
         * @param {string} provider - The provider of the payment option's provider
         * @param {number} paymentOptionId - The id of the payment option handling the transaction
         * @param {object} processingValues - The processing values of the transaction
         * @return {undefined}
         */
    _processRedirectFlow: async function (providerCode, paymentOptionId, paymentMethodCode, processingValues) {
        if (providerCode !== 'eway') {
            this._super(...arguments);
            return;
        }

        if (processingValues['payment_flow'] === 'redirect_to_eway') {
            window.open(processingValues['SharedPaymentUrl'], "_self");
        }
        if (processingValues['payment_flow'] === 'from_odoo') {
            const inputs = this._getEwayInlineFormInputs(processingValues['provider_id']);
            return this.rpc('/payment/eway/get_provider_info', {    
                'paymentTransaction': processingValues.payment_transaction,
                'reference': processingValues.reference,
                'cardNumber': inputs.card.value.replace(/ /g, ''), // Remove all spaces
                'nameOnCard': inputs.name_on_card.value,
                'month': inputs.month.value,
                'year': inputs.year.value,
                'cardCode': inputs.code.value,      
            }).then(() => {
                window.location = '/payment/status';
            })
            .catch((error) => {
                if (error instanceof RPCError) {
                    this._displayErrorDialog(_t("Payment processing failed"), error.data.message);
                    this._enableButton();
                } else {
                    return Promise.reject(error);
                }
            });
        
        }
    },

    /**
         * Prepare the options to init the Eway JS Object
         *
         * Function overridden in internal module
         *
         * @param {object} processingValues
         * @return {object}
         */
    _prepareEwayOptions: function (processingValues) {
        return {};
    },


     /**
    * Redirect the customer to the status route.
    *
    * @private
    * @param {string} providerCode - The code of the selected payment option's provider.
    * @param {number} paymentOptionId - The id of the selected payment option.
    * @param {string} paymentMethodCode - The code of the selected payment method, if any.
    * @param {object} processingValues - The processing values of the transaction.
    * @return {void}
    */
   _processTokenFlow(providerCode, paymentOptionId, paymentMethodCode, processingValues) {
    // The flow is already completed as payments by tokens are immediately processed.
    if (providerCode !== 'eway') {
        this._super(...arguments);
        return;
    }
    if (processingValues['payment_flow'] === 'redirect_to_eway') {
        window.open(processingValues['SharedPaymentUrl'], "_self");
    }
    if (processingValues['payment_flow'] === 'from_odoo') {
        const inputs = this._getEwayInlineFormInputs(processingValues['provider_id']);
        return this.rpc('/payment/eway/get_provider_info', {    
            'paymentTransaction': processingValues.payment_transaction,
            'reference': processingValues.reference,
            'token_id' :   paymentOptionId,
        }).then(() => {
            window.location = '/payment/status';
        })
        .catch((error) => {
            if (error instanceof RPCError) {
                this._displayErrorDialog(_t("Payment processing failed"), error.data.message);
                this._enableButton();
            } else {
                return Promise.reject(error);
            }
        });
    
    }
   },  
});