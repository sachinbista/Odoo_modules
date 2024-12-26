/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";
import { SaleOrderLineProductField } from '@sale/js/sale_product_field';
import { ProductPriceEntryModal } from "@fds_sale/js/product_price_entry";


patch(SaleOrderLineProductField.prototype, 'fds_sale_price_entry', {

    setup() {
        this._super(...arguments);

        this.rpc = useService("rpc");
        this.ui = useService("ui");
    },

    async _onProductTemplateUpdate() {
        this._super(...arguments);
        const result = await this.orm.call(
            'product.template',
            'get_single_product_variant',
            [this.props.record.data.product_template_id[0]],
            {
                context: this.context,
            }
        );
        if(result && result.product_id) {
            if (this.props.record.data.product_id != result.product_id.id) {
                await this.props.record.update({
                    product_id: [result.product_id, result.product_name],
                });
                if (result.is_both_MTO_BUY) {
                    this.is_both_MTO_BUY = true;
                    return this._openProductPriceEntry();
                }
            }
        }
    },

    async _openProductPriceEntry () {
        const productTemplateId = this.props.record.data.product_template_id[0];
        const productId = this.props.record.data.product_id[0];
        const $modal = $(
            await this.rpc(
                "/fds_sale/show_product_price_entry",
                {
                    product_template_id: productTemplateId,
                    product_id: productId,
                },
            )
        );
        const productSelector = `input[type="hidden"][name="product_id"], input[type="radio"][name="product_id"]:checked`;
        // TODO VFE drop this selectOrCreate and make it so that
        // get_single_product_variant returns first variant as well.
        // and use specified product on edition mode.
        $modal.find(productSelector).val(productId);
        this.rootProduct = {
            product_id: productId,
            product_template_id: productTemplateId,
        };
        const productPriceEntryModel = new ProductPriceEntryModal(null, {
            rootProduct: this.rootProduct,
            okButtonText: this.env._t("Confirm"),
            cancelButtonText: this.env._t("Back"),
            title: this.env._t("Configure"),
            context: this.context,
        });
        let modalEl;
        productPriceEntryModel.opened(() => {
            modalEl = productPriceEntryModel.el;
            this.ui.activateElement(modalEl);
        });
        productPriceEntryModel.on("closed", null, async () => {
            // Wait for the event that caused the close to bubble
            await new Promise(resolve => setTimeout(resolve, 0));
            this.ui.deactivateElement(modalEl);
        });
        productPriceEntryModel.open();

        let confirmed = false;
        productPriceEntryModel.on("confirm", null, async () => {
            confirmed = true;
            const [
                mainProduct,
                ...optionalProducts
            ] = await productPriceEntryModel.getAndCreateSelectedProducts();

            await this.props.record.update(await this._convertProductPriceEntryDataToUpdateData(mainProduct));
            this._onProductUpdate();
        });
        productPriceEntryModel.on("closed", null, () => {
            if (confirmed) {
                return;
            }
            if (mode != 'edit') {
                this.props.record.update({
                    product_template_id: false,
                    product_id: false,
                    price_entry: 1.0,
                });
            }
        });
    },

    async _convertProductPriceEntryDataToUpdateData(mainProduct) {
        const nameGet = await this.orm.nameGet(
            'product.product',
            [mainProduct.product_id],
            { context: this.context }
        );
        let result = {
            product_id: nameGet[0],
            price_unit: mainProduct.price_entry,
        };

        return result;
    },

});
