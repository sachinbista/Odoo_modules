/* @odoo-module */

import { registry } from "@web/core/registry";
import { listView } from "@web/views/list/list_view";
import { ListController } from "@web/views/list/list_controller";
import { ListRenderer } from "@web/views/list/list_renderer";
import { useService, useBus } from "@web/core/utils/hooks";

export class ListListController extends ListController {
        setup() {
            super.setup()
            this.orm = useService("orm");

        }

    async productCatalogOrderline() {
        if (this.model.root.editedRecord)
            {
                await this.model.root.editedRecord.save()
            }
        let product_list = []
        let order_id = this.props.context.order_id
        let self = this
        this.model.root.records.forEach((record) => {
//            if (record.selected)
//            {
//                const product_id = record.resId;
//                const quantity = record.data.catalog_prd_quantity || 1;
//                product_list.push({
//                    product_id: product_id,
//                    quantity: quantity
//                });
//            }
             const quantity = record.data.catalog_prd_quantity || 0;
                    if (quantity > 0) {
                        const product_id = record.resId;
                        product_list.push({
                            product_id: product_id,
                            quantity: quantity
                        });
                    }
            });
        await this.orm.call("sale.order.line", "add_catalog_lines", [[],product_list,order_id]).then((action)=>{
            self.actionService.doAction(action)
        });
        window.history.go(-1)

    }

};

ListListController.template = 'bista_product_catalog_extension.product_catalogUpdateListView';

export class ListListRenderer extends ListRenderer {

}
ListListRenderer.template= 'bista_product_catalog_extension.listRendererUpdate'
ListListRenderer.recordRowTemplate = 'bista_product_catalog_extension.listRendererRecordRowUpdate';


export const ListViewCatalog = {
    ...listView,
    Controller: ListListController,
    Renderer: ListListRenderer,
     buttonTemplate: 'bista_product_catalog_extension.product_catalogUpdateListViewButton',
};

registry.category("views").add("list_catalog_view", ListViewCatalog);
