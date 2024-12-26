/** @odoo-module */

import ajax from 'web.ajax';
import Dialog from 'web.Dialog';
import OwlDialog from 'web.OwlDialog';
import ServicesMixin from 'web.ServicesMixin';

export const ProductPriceEntryModal = Dialog.extend(ServicesMixin, {
    events:  _.extend({}, Dialog.prototype.events, {}),
    /**
     * Initializes the optional products modal
     *
     * @override
     * @param {$.Element} parent The parent container
     * @param {Object} params
     * @param {string} params.okButtonText The text to apply on the "ok" button, typically
     *   "Add" for the sale order and "Proceed to checkout" on the web shop
     * @param {string} params.cancelButtonText same as "params.okButtonText" but
     *   for the cancel button
     * @param {integer} params.previousModalHeight used to configure a min height on the modal-content.
     *   This parameter is provided by the product configurator to "cover" its modal by making
     *   this one big enough. This way the user can't see multiple buttons (which can be confusing).
     * @param {Object} params.rootProduct The root product of the optional products window
     */
    init: function (parent, params) {
        var self = this;

        var options = _.extend({
            size: 'medium',
            buttons: [{
                text: params.okButtonText,
                click: this._onConfirmButtonClick,
                classes: 'btn-primary'
            }, {
                text: params.cancelButtonText,
                click: this._onCancelButtonClick
            }],
            technical: !params.isWebsite,
        }, params || {});

        this._super(parent, options);

        this.context = params.context;
        this.rootProduct = params.rootProduct;
        this.container = parent;
        this.previousModalHeight = params.previousModalHeight;
        this.dialogClass = 'oe_product_price_entry_modal';
        this._productImageField = 'image_128';

        this._opened.then(function () {
            if (self.previousModalHeight) {
                self.$el.closest('.modal-content').css('min-height', self.previousModalHeight + 'px');
            }
        });
    },
     /**
     * @override
     */
    willStart: function () {
        var self = this;

        var uri = "/fds_sale/show_product_price_entry";
        var getModalContent = ajax.jsonRpc(uri, 'call', {
            product_template_id: self.rootProduct.product_template_id,
            product_id: self.rootProduct.product_id,
        })
        .then(function (modalContent) {
            if (modalContent) {
                var $modalContent = $(modalContent);
                $modalContent = self._postProcessContent($modalContent);
                self.$content = $modalContent;
            } else {
                self.trigger('options_empty');
                self.preventOpening = true;
            }
        });

        var parentInit = self._super.apply(self, arguments);
        return Promise.all([getModalContent, parentInit]);
    },

    /**
     * This is overridden to append the modal to the provided container (see init("parent")).
     * We need this to have the modal contained in the web shop product form.
     * The additional products data will then be contained in the form and sent on submit.
     *
     * @override
     */
    open: function (options) {
        $('.tooltip').remove(); // remove open tooltip if any to prevent them staying when modal is opened

        var self = this;
        this.appendTo($('<div/>')).then(function () {
            if (!self.preventOpening) {
                self.$modal.find(".modal-body").replaceWith(self.$el);
                self.$modal.attr('open', true);
                self.$modal.removeAttr("aria-hidden");
                self.$modal.modal().appendTo(self.container);
                const modal = new Modal(self.$modal[0], {
                    focus: true,
                });
                modal.show();
                self._openedResolver();

                // Notifies OwlDialog to adjust focus/active properties on owl dialogs
                OwlDialog.display(self);
            }
        });
        if (options && options.shouldFocusButtons) {
            self._onFocusControlButton();
        }

        return self;
    },
    /**
     * Will update quantity input to synchronize with previous window
     *
     * @override
     */
    start: function () {
        var def = this._super.apply(this, arguments);
        var self = this;

        // set a unique id to each row for options hierarchy
        // var $products = this.$el.find('tr.js_product');
        // _.each($products, function (el) {
        //     var $el = $(el);
        //     var uniqueId = self._getUniqueId(el);

        //     var productId = parseInt($el.find('input.product_id').val(), 10);
        //     if (productId === self.rootProduct.product_id) {
        //         self.rootProduct.unique_id = uniqueId;
        //     } else {
        //         el.dataset.parentUniqueId = self.rootProduct.unique_id;
        //     }
        // });

        return def
    },

    // ------------------------------------------
    // Private
    // ------------------------------------------

    /**
     * Adds the product image and updates the product description
     * based on attribute values that are either "no variant" or "custom".
     *
     * @private
     */
    _postProcessContent: function ($modalContent) {
        return $modalContent;
    },

    /**
     * @private
     */
    _onConfirmButtonClick: function () {
        this.trigger('confirm');
        this.close();
    },

    /**
     * @private
     */
    _onCancelButtonClick: function () {
        this.trigger('back');
        this.close();
    },
    /**
     * Returns a unique id for `$el`.
     *
     * @private
     * @param {Element} el
     * @returns {integer}
     */
    _getUniqueId: function (el) {
        if (!el.dataset.uniqueId) {
            el.dataset.uniqueId = parseInt(_.uniqueId(), 10);
        }
        return el.dataset.uniqueId;
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * Returns the list of selected products.
     * The root product is added on top of the list.
     *
     * @returns {Array} products
     *   {integer} product_id
     *   {integer} quantity
     *   {Array} product_custom_variant_values
     *   {Array} no_variant_attribute_values
     * @public
     */
    getAndCreateSelectedProducts: async function () {
        var self = this;
        const products = [];
        for (const product of self.$modal.find('.js_product.in_cart')) {
            var $item = $(product);
            var price_entry = parseFloat($item.find('input[name="price_entry"]').val().replace(',', '.') || 1);
            var parentUniqueId = product.dataset.parentUniqueId;
            var uniqueId = product.dataset.uniqueId;

            products.push({
                'product_id': parseInt($item.find('input.product_id').val(), 10),
                'product_template_id': parseInt($item.find('input.product_template_id').val(), 10),
                'price_entry': price_entry,
                'parent_unique_id': parentUniqueId,
                'unique_id': uniqueId,
            });
        }
        return products;
    },
});
