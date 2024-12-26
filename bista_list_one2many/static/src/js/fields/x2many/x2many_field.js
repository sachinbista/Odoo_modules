/** @odoo-module **/

import {X2ManyField} from "@web/views/fields/x2many/x2many_field";
import {patch} from '@web/core/utils/patch';

patch(X2ManyField.prototype, 'bista_list_o2m.X2ManyField', {
    setup() {
        this._super();
        this.isNestedList = this.activeField.viewType === 'list';
    },

    get rendererProps() {
        const result = this._super();
        Object.assign(result, {
            isNestedList: this.isNestedList,
            nestedFieldName: this.props.name,
        });
        return result;
    },

    get pagerProps() {
        const list = this.list;
        return {
            offset: list.offset,
            limit: list.limit,
            total: list.count,
            onUpdate: async ({ offset, limit }) => {
                const initialLimit = this.list.limit;
                const unselected = await list.unselectRecord(true);
                if (unselected || this.isNestedList) {
                    if (initialLimit === limit && initialLimit === this.list.limit + 1) {
                        // Unselecting the edited record might have abandonned it. If the page
                        // size was reached before that record was created, the limit was temporarily
                        // increased to keep that new record in the current page, and abandonning it
                        // decreased this limit back to it's initial value, so we keep this into
                        // account in the offset/limit update we're about to do.
                        offset -= 1;
                        limit -= 1;
                    }
                    if (this.isNestedList) {
                        list.offset = offset;
                        list.limit = limit;
                    }
                    await list.load({ limit, offset });
                    this.render();
                }
            },
            withAccessKey: false,
        };
    }
});
