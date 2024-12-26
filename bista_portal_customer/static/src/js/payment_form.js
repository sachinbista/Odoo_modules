/** @odoo-module **/
import publicWidget from '@web/legacy/js/public/public_widget';
// import { _t } from '@web/core/l10n/translation';

// publicWidget.registry.PaymentForm = publicWidget.registry.PaymentForm.extend({
//     events: Object.assign({}, publicWidget.registry.PaymentForm.prototype.events, {
//         'click [name="o_without_payment_submit_button"]': '_submitFormWithoutPayment',
//     }),
//     async _submitFormWithoutPayment(ev) {
//         debugger;
//     }
// });

// export default publicWidget.registry.PaymentForm;

debugger;

publicWidget.registry.PaymentForm.include({
    events: Object.assign({}, publicWidget.registry.PaymentForm.prototype.events, {
        'click [name="o_without_payment_submit_button"]': '_submitFormWithoutPayment',
    }),
    async _submitFormWithoutPayment(ev) {
        debugger;
    }
});
