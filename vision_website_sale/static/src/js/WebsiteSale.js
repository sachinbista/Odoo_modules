/** @odoo-module **/
import publicWidget from "@web/legacy/js/public/public_widget";
import wSaleUtils from "@website_sale/js/website_sale_utils";

publicWidget.registry.WebsiteSale.include({
    start() {
        const def = this._super(...arguments);
        this.$el = $(this.el)
        this.service_field = this.$el.find("#service_ids")
        this.variant_size_table = this.$el.find(".variant_size_table")
        this.service_field.on("change", this.onServiceChange.bind(this))
        this.variantQuantities = {}
        this.service_price = this.$el.find(".service_price")
        this.error_message = this.$el.find(".size_chart_error")
        this.service_price_amount = this.service_price.find(".service_price_amount")
        this.service_container = this.$el.find("#service_container")
        this.no_product = this.$el.find("#no_product")
        return def;
    },


    onChangeVariant: function (ev) {
        const def = this._super(...arguments);
        this.variantQuantities = {}
        this.service_price_list = {}
        this.getSelectedAttribute();
        this.product_template_id = $('input[name*="product_template"]').val()
        this.getCompatibleService()
        return def
    },

    getSelectedAttribute() {
        let otherAttributes = this.$el.find("#otherAttributes").val()
        let sizeAttribute = this.$el.find("#sizeAttribute").val()
        let selectedAttributes = [];
        otherAttributes = JSON.parse(otherAttributes);
        otherAttributes.forEach(attributeId => {
            let selectedAttributeElements = $(`ul[data-attribute_id='${attributeId}']`).find("input:checked");
            selectedAttributeElements.each(function() {
                selectedAttributes.push($(this).val());
            });
        });
        this.otherAttributes = selectedAttributes;

        let sizeList = $(`li[data-attribute_id='${sizeAttribute}']`)
        sizeList.hide()
        $(".js_add_cart_variants").show()


    },

    async getCompatibleService() {
        let service_ids = await this.rpc("/product/getServices", {
            product_id: this.product_template_id,
            other_attributes: this.otherAttributes
        })

        let self = this;
        let placeholder = $('<option selected="selected" value="">Select Option</option>')
        this.service_field.empty()
        this.service_field.append(placeholder)

        if (service_ids.list.length) {
            this.service_container.removeClass("d-none")
            this.service_container.addClass("d-flex")
            service_ids.list.forEach(function (service) {
                self.service_price_list[service.id] = self.toMonetary(service.list_price, service_ids.currency)
                self.service_field.append(
                    $(`<option value='${service.id}'>${service.display_name}</option>`)
                )
            })
        } else {
            this.service_container.addClass('d-none')
            this.service_container.removeClass('d-flex')
        }

        this.onServiceChange()
    },


    toMonetary(num, currency) {
        let amount = num.toLocaleString('en-US', {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2
        })
        return currency.symbol + amount;
    },

    async onServiceChange() {
        this.service_id = this.service_field.val()
        let self = this;
        let variant_ids = await this.rpc("/product/getVariants", {
            product_id: this.product_template_id,
            service_id: this.service_id,
            other_attributes: this.otherAttributes
        })

        if (!variant_ids) {
            this.no_product.show()
        } else {
            this.no_product.hide()
        }

        let price = this.service_price_list[this.service_id]

        if (this.service_id && price) {
            this.service_price.show()
            this.service_price_amount.val(price)
        } else {
            this.service_price.hide()
            this.service_price_amount.val(0)
        }
        let header = this.variant_size_table.find("thead").find("tr")
        let body = this.variant_size_table.find("tbody").find('tr')

        header.empty()
        body.empty()
        header.append("<th>Size(s)</th>")
        body.append("<td class='td-bg'>Quantity</td>")
        for (var size in variant_ids) {
            header.append(
                `<th>${size}</th>`
            )
            let variant_id = variant_ids[size]
            let input = $(`<input id=\"${variant_id}\" min="1" type=\"number\" value=\"0\" name=\"variant_size_qty\"/>`)
            let column = $("<td></td>")
            column.append(input)
            body.append(column)
            input.on('change', function () {
                self.variantQuantities[variant_id] = parseInt($(this).val())
                self._hideError();
            })

        }


    },


    _hideError() {
        this.error_message.hide()
    },

    _validateQuantity() {
        if (!Object.keys(this.variantQuantities).length) {
            this.error_message.show()
            return false
        }
        return true
    },

    _onClickAdd: function (ev) {
        ev.preventDefault();
        if (!this._validateQuantity()) {
            return
        }

        let total_qty = 0;
        let param_list = []
        for (let product_id in this.variantQuantities) {
            let qty = this.variantQuantities[product_id]
            total_qty += qty;
            let params = {
                add_qty: qty,
                no_variant_attribute_values: "[]",
                product_custom_attribute_values: "[]",
                product_id: parseInt(product_id),
                variant_values: [],
                service_id: this.service_id,
            }
            param_list.push(params)
        }

        if (this.service_id) {
            let params = {
                add_qty: total_qty,
                no_variant_attribute_values: "[]",
                product_custom_attribute_values: "[]",
                product_id: parseInt(this.service_id),
                variant_values: []
            }
            param_list.push(params)
        }

        console.log("Varaints ", )
        this._addToCartInPage(param_list)

    },

    async _addToCartInPage(params_list) {
        let notification_info = "Cart is updated";
        let last_data = false;
        console.log("Website Sale Util ", wSaleUtils)
        for (const params of params_list) {
            const data = await this.rpc("/shop/cart/update_json", {
                ...params,
                display: false,
                force_create: true,
            });
            if (data.cart_quantity && (data.cart_quantity !== parseInt($(".my_cart_quantity").text()))) {
                wSaleUtils.updateCartNavBar(data);
            }
            notification_info = data.notification_info
            last_data = data
        }
        wSaleUtils.showCartNotification(this.call.bind(this), notification_info);
        return last_data;
    },

});
