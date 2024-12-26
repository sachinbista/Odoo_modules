/** @odoo-module */

import session from 'web.session'
import { useService } from "@web/core/utils/hooks";
import { useEnv } from "@odoo/owl";

/**
 * Redirect to the sub partner kanban view.
 *
 * @private
 * @param {MouseEvent} event
 * @returns {Promise} action loaded
 *
 */
export function onPartnerSubRedirect() {
    const actionService = useService('action');
    const orm = useService('orm');
    const rpc = useService('rpc');
    const env = useEnv();

    return async (event) => {
        const partnerId = parseInt(event.currentTarget.dataset.partnerId);
        if (!partnerId) {
            return {};
        }
        const type = event.currentTarget.dataset.type || 'direct';
        // Get subordonates of an partner through a rpc call.
        const subordinateIds = await rpc('/partner/get_subordinates', {
            partner_id: partnerId,
            subordinates_type: type,
            context: session.user_context
        });
        let action = await orm.call('res.partner', 'get_formview_action', [partnerId]);
        action = {...action,
            name: env._t('Team'),
            view_mode: 'kanban,list,form',
            views: [[false, 'kanban'], [false, 'list'], [false, 'form']],
            domain: [['id', 'in', subordinateIds]],
            res_id: false,
            context: {
                default_parent_id: partnerId,
            }
        };
        actionService.doAction(action);
    };
}
