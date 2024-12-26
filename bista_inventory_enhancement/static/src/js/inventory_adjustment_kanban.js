/** @odoo-module */

import { registry } from '@web/core/registry';
import { kanbanView } from '@web/views/kanban/kanban_view';
import { KanbanRecord } from '@web/views/kanban/kanban_record';
import { KanbanRenderer } from '@web/views/kanban/kanban_renderer';

export class CountBarcodeKanbanRecord extends KanbanRecord {
    onGlobalClick(ev) {
      if (this.props.record.resModel === "stock.inventory") {
        ev.currentTarget.getElementsByClassName('orchestrator_button').action_client_action_inventory.click();
      }
    }
    
}

export class CountBarcodeKanbanRenderer extends KanbanRenderer {}

CountBarcodeKanbanRenderer.components = {
    ...CountBarcodeKanbanRenderer.components,
    KanbanRecord: CountBarcodeKanbanRecord,
}

registry.category('views').add('stock_barcode_count_kanban', {
    ...kanbanView,
    Renderer: CountBarcodeKanbanRenderer,
});