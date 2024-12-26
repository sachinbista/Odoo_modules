/** @odoo-module */

import {Field} from '@web/views/fields/field';
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { usePopover } from "@web/core/popover/popover_hook";
import { onPartnerSubRedirect } from './hooks';

const { Component, onWillStart, onWillRender, onWillUpdateProps, useState } = owl;

function useUniquePopover() {
    const popover = usePopover();
    let remove = null;
    return Object.assign(Object.create(popover), {
        add(target, component, props, options) {
            if (remove) {
                remove();
            }
            remove = popover.add(target, component, props, options);
            return () => {
                remove();
                remove = null;
            };
        },
    });
}

class PartnerOrgChartPopover extends Component {
    async setup() {
        super.setup();

        this.rpc = useService('rpc');
        this.orm = useService('orm');
        this.actionService = useService("action");
        this._onPartnerSubRedirect = onPartnerSubRedirect();
    }

    /**
     * Redirect to the partner form view.
     *
     * @private
     * @param {MouseEvent} event
     * @returns {Promise} action loaded
     */
    async _onPartnerRedirect(partnerId) {
        const action = await this.orm.call('res.partner', 'get_formview_action', [partnerId]);
        this.actionService.doAction(action);
    }
}
PartnerOrgChartPopover.template = 'bista_contacts.partner_orgchart_partner_popover';
export class PartnerOrgChart extends Field {
    async setup() {
        super.setup();
        this.rpc = useService('rpc');
        this.orm = useService('orm');
        this.actionService = useService("action");
        this.popover = useUniquePopover();

        this.jsonStringify = JSON.stringify;

        this.state = useState({'partner_id': null});
        this.last_child_count = this.props.record.data.child_ids.records.length;
        this._onPartnerSubRedirect = onPartnerSubRedirect();

        onWillStart(this.handleComponentUpdate.bind(this));
        onWillRender(this.handleComponentUpdate.bind(this));
        onWillUpdateProps(this.handleComponentUpdate.bind(this));
    }

    /**
     * Called on start and on render
     */
    async handleComponentUpdate() {
        this.partner = this.props.record.data;
        // the widget is either dispayed in the context of a res.partner form or a res.users form
        this.state.partner_id = this.partner.employee_ids !== undefined ? this.partner.employee_ids.resIds[0] : this.partner.id;
        const is_reload = this.last_child_count != this.partner.child_ids.records.length;
        const forceReload = this.lastRecord !== this.props.record || is_reload;
        console.log(this, is_reload)
        this.lastRecord = this.props.record;
        await this.fetchPartnerData(this.state.partner_id, forceReload);
    }

    async fetchPartnerData(partnerId, force = false) {
        if (!partnerId) {
            this.managers = [];
            this.children = [];
            if (this.view_partner_id) {
                this.render(true);
            }
            this.view_partner_id = null;
        } else if (partnerId !== this.view_partner_id || force) {
            this.view_partner_id = partnerId;
            var orgData = await this.rpc(
                '/partner/get_org_chart',
                {
                    partner_id: partnerId,
                    context: Component.env.session.user_context,
                }
            );
            if (Object.keys(orgData).length === 0) {
                orgData = {
                    managers: [],
                    children: [],
                }
            }
            this.managers = orgData.managers;
            this.children = orgData.children;
            this.managers_more = orgData.managers_more;
            this.self = orgData.self;
            this.render(true);
        }
    }

    _onOpenPopover(event, partner) {
        this.popover.add(
            event.currentTarget,
            this.constructor.components.Popover,
            {partner},
            {closeOnClickAway: true}
        );
    }

    /**
     * Redirect to the partner form view.
     *
     * @private
     * @param {MouseEvent} event
     * @returns {Promise} action loaded
     */
    async _onPartnerRedirect(partnerId) {
        const action = await this.orm.call('res.partner', 'get_formview_action', [partnerId]);
        this.actionService.doAction(action);
    }

    async _onPartnerMoreManager(managerId) {
        await this.fetchPartnerData(managerId);
        this.state.partner_id = managerId;
    }
}

PartnerOrgChart.components = {
    Popover: PartnerOrgChartPopover,
};

PartnerOrgChart.template = 'bista_contacts.partner_org_chart';

registry.category("fields").add("contact_org_chart", PartnerOrgChart);


