odoo.define('fds_sale.  ', function (require) {
    'use strict';

    var publicWidget = require('web.public.widget');
    var ProductConfiguratorDialog = require('fds_customer_rfq_portal.ProductConfiguratorDialog');

    publicWidget.registry.EditSaleOrder = publicWidget.Widget.extend({
        
        selector: '.js_sale_order_edit',

        events: {
            'click #addBtn': '_onClickAddButton',
            'click button.remove': '_onClickRemoveButton',
            // 'change .js-product-select': '_onChangeProudctId',
        },

        /**
        * @override
        */
        start: function () {
            var self = this;
            var def = this._super.apply(this, arguments);
            // Set select as select2
            const $selects = this.$el.find('.js-product-select');
            self.delete_ids = $('#js_temp_delete_line');
            self.index = 1;
            // selects.select2( {
            //     theme: 'bootstrap-5',
            //     dropdownAutoWidth : true
            // });
            $selects.selectpicker({
                liveSearch: true,
                liveSearchPlaceholder: 'Enter product name...',
                size: 7,
                dropupAuto: false,
            });
            $selects.on('changed.bs.select', function (e, clickedIndex, isSelected, previousValue) {
                self._onChangeProudctTemplateId(e)
            });

            // ------------------------------------------------------
            // BLOCK FORM'SUBMIT REQUEST ON REFRESH
            // ------------------------------------------------------

            if (window.history.replaceState) {
                window.history.replaceState(null, null, window.location.href);
            }

            // ------------------------------------------------------
            // BLOCK FORM'SUBMIT REQUEST ON REFRESH
            // ------------------------------------------------------

            return def
        },
        
        _onClickAddButton: function () {
            var self = this;
            var rowIdx = 0;
            var rowCount = self.index;
            var rowIdx = rowIdx + 1;
            var productSelectName = String(rowCount) + "_new-product_template_id";
            var productqty = String(rowCount) + "_new-product_uom_qty";
            var customProducts = String(rowCount)+ "_new-custom_products";
            var productOptions = $(document).find("#js_id_product_list").html();
            var text = `
            <tr id="${rowCount}_new">
                <td id="product_name"><span class="js_product_name" t-field="line.name"/></td> 
                <td class="row-index text-center">
                    <input class="form-control js_temp_product_id d-none" type="text" value="" name="${rowCount}_new-product_id" />
                    <input class="form-control js_temp_custom_products d-none" type="text" value="[]" name="${customProducts}">
                    <select class="form-control form-field js-product-select" name="${productSelectName}" required="True">
                        ${productOptions}
                    </select>
                </td>
                <td class="text-right">
                    <div id="" class="d-flex">
                        <input class="form-control line-product_uom_qty mr8" name="${productqty}" type="number" step="any" value="1.0"/>
                        <span>Units</span>
                    </div>
                </td>
                <td class="text-right">
                    <div class="total-price text-right">1.00</div>
                </td>
                <td class="text-center"><button class="btn btn-danger remove" type="button"><i class="fa fa-trash"/></button></td>
            </tr>
            `

            $("#tbody").append(text);
            self.index += 1
            // $('select[name="' + productSelectName + '"]').select2({
            //     theme: 'bootstrap-5',
            //     dropdownAutoWidth : true
            // });
            var $select = $(`tr#${rowCount}_new`).find('.js-product-select')
            $select.selectpicker({
                liveSearch: true,
                liveSearchPlaceholder: 'Enter product name...',
                size: 7,
                dropupAuto: false,
            });
            $select.on('changed.bs.select', function (e, clickedIndex, isSelected, previousValue) {
                self._onChangeProudctTemplateId(e)
            });
        },
        
        _onClickRemoveButton: function (ev) {
            var self = this;
            var $tr = $(ev.currentTarget).closest("tr");
            if ($tr.attr('id') && !$tr.attr('id').includes("_new")) {
                var value = self.delete_ids.val();
                value = value ? (value + ',' + $tr.attr('id')) : $tr.attr('id');
                self.delete_ids.val(value);
            }
            $tr.remove()
        },

        _onChangeProudctTemplateId: function (ev) {
            const self = this;
            var $product = $(ev.currentTarget);
            var productTemplateId = $product.find("option:selected").val();
            var $productImg = $product.closest("tr").find(".js_product_img");
            $productImg.attr("src", '/web/static/img/placeholder.png');
    
            $.ajax({
                url: "/get-single-product-variant",
                data: { product_template_id: productTemplateId },
                type: "post",
                cache: false,
                success: function (result) {
                    var datas = JSON.parse(result);
                    if (datas.product_id) {
                        self._updateProductInfo($product.closest("tr"), datas)
                    } else if (datas.product_ids) {
                        // Get product configurator
                        self._openProductConfigurator(
                            $product.closest("tr"),
                            productTemplateId,
                        )
                    }
                },
            });
        },

        _updateProductInfo: function($product, product) {
            // var $productImg = $product.find(".js_product_img");
            var $productId = $product.find(".js_temp_product_id");
            var $productName = $product.find(".js_product_name");
            var $customeProducts = $product.find(".js_temp_custom_products");
            if (!product.product_id) {
                // Empty Product template
                $product.find(".js_product_id").val('');
            }
            // $productImg.attr("src", product.image || '/web/static/img/placeholder.png');
            $productId.attr("value", product.product_id || '');
            
            var productName = product.product_name
            if (product.product_custom_attribute_values) {
                _.each(product.product_custom_attribute_values, function (custom) {
                    productName += '<br/>' + custom.attribute_name + ': ' + custom.attribute_value_name + ': ' + custom.custom_value
                })
                $customeProducts.attr("value", JSON.stringify(product.product_custom_attribute_values));
            }
            $productName.html(productName || '');
        },

        _openProductConfigurator: async function ($product, productTemplateId) {
            var $content = $(
                await this._rpc({
                    route: "/fds_product_configurator/configure",
                    params: {
                        product_template_id: productTemplateId,
                    },
                }
            ))
            new ProductConfiguratorDialog(this, {
                $content,
                $product,
                callBackConfirm: this._updateProductInfo
            }).open();

        }
    })

});