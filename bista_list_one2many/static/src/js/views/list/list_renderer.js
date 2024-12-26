
/** @odoo-module */

import {ListRenderer} from '@web/views/list/list_renderer';
import {KanbanRenderer} from '@web/views/kanban/kanban_renderer';
import {patch} from '@web/core/utils/patch';
import {useService} from "@web/core/utils/hooks";
import {FormViewDialog} from "@web/views/view_dialogs/form_view_dialog";

patch(ListRenderer.prototype, 'bista_list_o2m.ListRenderer', {
    setup() {
        this._super();
        this.dialogService = useService('dialog');
    },

    get canResequenceRows() {
        if (this.props.isNestedList) return false;
        return this._super();
    },

    get getEmptyRowIds() {
        if (this.props.isNestedList) return [];
        return this._super();
    },

    async onCellClicked(record, column, ev) {
//        ev.stopPropagation();
        let targetId = $(ev.target).closest("td.o_data_cell").find("div:eq(1)")
        if (targetId.hasClass("invisible") || $(ev.target)[0].className == 'o_data_cell'
            || $(ev.target)[0].className == 'fa fa-area-chart text-primary' ||
            $(ev.target)[0].className == 'fa fa-area-chart text-danger' ||
            $(ev.target)[0].className == 'fa fa-fw o_button_icon fa-list text-primary' ||
            $(ev.target)[0].className == 'fa fa-fw o_button_icon fa-list text-danger' ||
            $(ev.target).attr("data-tooltip") == "No records") {
            return false
        }
        if (this.props.isNestedList) {
            return false
            // this.dialogService.add(FormViewDialog, {
            //     context: record.context,
            //     resId: record.resId,
            //     resModel: record.resModel,
            //     mode: 'readonly',
            //     preventCreate: true,
            //     preventEdit: true,
            // });
        } else {
            this._super(...arguments);
        }
    },
//
    onClickSortColumn(column, ev) {
        if (this.props.isNestedList) {
            ev.stopPropagation();
        }
        this._super(...arguments);
    },

    onStartResize(ev) {
        if (this.props.isNestedList) {
            ev.stopPropagation();
            this.resizing = true;
            const table = this.tableRef.el;
            const th = ev.target.closest("th");
            const handler = th.querySelector(".o_resize");
            table.style.width = `${Math.floor(table.getBoundingClientRect().width)}px`;
            const thPosition = [...th.parentNode.children].indexOf(th);
            const resizingColumnElements = [...table.getElementsByTagName("tr")]
                .filter((tr) => tr.children.length === th.parentNode.children.length)
                .map((tr) => tr.children[thPosition]);
            const initialX = ev.clientX;
            const initialWidth = th.getBoundingClientRect().width;
            const initialTableWidth = table.getBoundingClientRect().width;
            const resizeStoppingEvents = ["keydown", "mousedown", "mouseup"];

            // fix the width so that if the resize overflows, it doesn't affect the layout of the parent
            if (!this.rootRef.el.style.width) {
                this.rootRef.el.style.width = `${Math.floor(
                    this.rootRef.el.getBoundingClientRect().width
                )}px`;
            }

            // Apply classes to table and selected column
            table.classList.add("o_resizing");
            for (const el of resizingColumnElements) {
                el.classList.add("o_column_resizing");
                handler.classList.add("bg-primary", "opacity-100");
                handler.classList.remove("bg-black-25", "opacity-50-hover");
            }
            // Mousemove event : resize header
            const resizeHeader = (ev) => {
                ev.preventDefault();
                ev.stopPropagation();
                const delta = ev.clientX - initialX;
                const newWidth = Math.max(10, initialWidth + delta);
                const tableDelta = newWidth - initialWidth;
                th.style.width = `${Math.floor(newWidth)}px`;
                th.style.maxWidth = `${Math.floor(newWidth)}px`;
                table.style.width = `${Math.floor(initialTableWidth + tableDelta)}px`;
            };
            window.addEventListener("mousemove", resizeHeader);

            // Mouse or keyboard events : stop resize
            const stopResize = (ev) => {
                this.resizing = false;
                // freeze column size after resizing
                this.keepColumnWidths = true;
                // Ignores the 'left mouse button down' event as it used to start resizing
                if (ev.type === "mousedown" && ev.which === 1) {
                    return;
                }
                ev.preventDefault();
                ev.stopPropagation();

                table.classList.remove("o_resizing");
                for (const el of resizingColumnElements) {
                    el.classList.remove("o_column_resizing");
                    handler.classList.remove("bg-primary", "opacity-100");
                    handler.classList.add("bg-black-25", "opacity-50-hover");
                }

                window.removeEventListener("mousemove", resizeHeader);
                for (const eventType of resizeStoppingEvents) {
                    window.removeEventListener(eventType, stopResize);
                }

                // we remove the focus to make sure that the there is no focus inside
                // the tr.  If that is the case, there is some css to darken the whole
                // thead, and it looks quite weird with the small css hover effect.
                document.activeElement.blur();

                const tds = th.closest('tr').children;
                const tbodies = $(`[name="${this.props.nestedFieldName}"] table:not(:first) > tbody`);
                _.each(tbodies, tbody => {
                    const $tr = $(tbody).find('tr:first');
                    if ($tr.length) {
                        _.each(tds, (td, index) => {
                            $tr[0].children[index].style.maxWidth = td.style.maxWidth;
                            $tr[0].children[index].style.width = td.style.width;
                        });
                        const otherTable = $tr.closest('table')[0];
                        otherTable.style.width = table.style.width;
                    }
                });
            };
            // We have to listen to several events to properly stop the resizing function. Those are:
            // - mousedown (e.g. pressing right click)
            // - mouseup : logical flow of the resizing feature (drag & drop)
            // - keydown : (e.g. pressing 'Alt' + 'Tab' or 'Windows' key)
            for (const eventType of resizeStoppingEvents) {
                window.addEventListener(eventType, stopResize);
            }
        } else {
            this._super(...arguments);
        }
    },
});

ListRenderer.props = [
    ...ListRenderer.props,
    'isNestedList?',
    'nestedFieldName?',
];
KanbanRenderer.props = [
    ...KanbanRenderer.props,
    'isNestedList?',
    'nestedFieldName?',
];