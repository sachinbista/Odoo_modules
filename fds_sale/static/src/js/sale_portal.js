/** @odoo-module */

import publicWidget from 'web.public.widget';

publicWidget.registry.PortalHomeCounters.include({
    /**
     * @override
     */
    _getCountersAlwaysDisplayed() {
        return this._super(...arguments).concat([
            'quotation_count',
            'order_count',
            'committed_quotation_count',
            'estimate_quotation_count',
        ]);
    },
});
