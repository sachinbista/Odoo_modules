odoo.define('bista_product_engraving.product_engraving', function (require) {
    "use strict";

    var publicWidget = require('web.public.widget');
    var VariantMixin = require('website_sale.VariantMixin');

    publicWidget.registry.AddEngravingWidget = publicWidget.Widget.extend(VariantMixin, {
        selector: '#engrave-section',
        events: {
            'click input[name="showEngrav"]': '_onClickShowEngraving',
            'keyup input.engraving_text': '_onEngravingTextChange',
            'click .font-style-list': '_onFontStyleClick',
        },

        start: function () {
            this.$engravingSection = this.$el.find('#engrave-content');
            this.$engravingPreview = this.$el.find('#engravingPreview');
            this.currentEngraveText = '';
            this.currentEngraveFont = '';
            this.showEngrav = false;
            return this._super.apply(this, arguments);
        },


        updateEngraveTextSelection: function (updateTextValueOnly=false) {
            var $inputs = $('#product_details input.js_variant_change, select.js_variant_change option');
            var showEngrav = this.showEngrav;
            var currentEngraveText = this.currentEngraveText;
            if ($inputs.length) {
                // looping through all inputs and select the one which has data-attribute_id="643"
                $inputs.each(function (index, input) {
                    let $input = $(input);
                    let $variant_attribute = $input.closest('li.variant_attribute');
                    let is_engrave = $variant_attribute.data('is_engrave');
                    let engrave_style = $variant_attribute.data('engrave_style');
                    if (is_engrave && engrave_style === 'engrave_text') {
                        // TODO: need to add is_none data attribute
                        // let is_none = $input.data('is_none');
                        let is_none = $input.data('value_name') === 'None';
                        if (updateTextValueOnly && !is_none) {
                            let value_id = $input.data('value_id');
                            $variant_attribute.find('input[data-custom_product_template_attribute_value_id="'+value_id+'"]').val(currentEngraveText);
                            // $input.val(this.currentEngraveText);
                            // $input.trigger('change');
                            return;
                        }
                        if (showEngrav === '0') {
                            if (is_none) {
                                $input.prop('checked', true);
                                // FIX: reduncy of code
                                if ($input.is('input[type="radio"]')) {
                                    $input.prop('checked', true);
                                    $input.trigger('change');
                                } else if ($input.is('option')) {
                                    $input.prop('selected', true);
                                    $input.trigger('change');
                                }
                                return;
                            }
                        } else if (showEngrav === '1') {
                            if (!is_none) {
                                $input.prop('checked', true);
                                // FIX: reduncy of code
                                if ($input.is('input[type="radio"]')) {
                                    $input.prop('checked', true);
                                    $input.trigger('change');
                                } else if ($input.is('option')) {
                                    $input.prop('selected', true);
                                    $input.trigger('change');
                                }
                                return;
                            }
                        }
       
                        
                    } 
                });
            }

        },
            
        _onClickShowEngraving: function (ev) {
            let showEngrav = $(ev.currentTarget).val();
            this.showEngrav = showEngrav;
            // TODO: need to make common function for show/hide
            if (showEngrav === '1') {
                this.$engravingSection.show();
                this.$engravingSection.removeClass('d-none');
                // select Engrave Text attribute value
            } else {
                this.$engravingSection.hide();
                this.$engravingSection.addClass('d-none');
            }
            this.updateEngraveTextSelection(false);
        },

        _onEngravingTextChange: function (ev) {
            let engraving_text = $(ev.currentTarget).val();
            this.currentEngraveText = engraving_text;
            // this.updateEngraveTextSelection(true);
            // let $engravingPreview = this.$el.find('#engravingPreview');
            this.$engravingPreview.text(engraving_text);
        },

        _onFontStyleClick: function (ev) {
            ev.preventDefault();
            let $fontStyle = $(ev.currentTarget);
            let font_style = $fontStyle.data('value');
            this.currentEngraveFont = font_style;
            this.$el.find('#selectedfontstyle').val(font_style);
            this.$el.find('#engraveFontid span.filter-option').text(font_style);
            this.$el.find('#engraveFontid span.filter-option').removeClass().addClass('filter-option pull-left').addClass(font_style);
            this.$engravingPreview.removeClass().addClass(font_style);
        }
    });

    // publicWidget.registry.EngraveWidget = publicWidget.Widget.extend({
    //     selector: '#engrave-content',
    //     events: {
    //         'keyup input.engraving_text': '_onEngravingTextChange',
    //         'click .font-style-list': '_onFontStyleClick',
    //     },

    //     start: function () {
    //         this.$engravingPreview = this.$el.find('#engravingPreview');
    //         return this._super.apply(this, arguments);
    //     },

    //     _onEngravingTextChange: function (ev) {
    //         let engraving_text = $(ev.currentTarget).val();
    //         // let $engravingPreview = this.$el.find('#engravingPreview');
    //         this.$engravingPreview.text(engraving_text);
    //     },

    //     _onFontStyleClick: function (ev) {
    //         ev.preventDefault();
    //         let $fontStyle = $(ev.currentTarget);
    //         let font_style = $fontStyle.data('value');
    //         this.$el.find('#selectedfontstyle').val(font_style);
    //         this.$el.find('#engraveFontid span.filter-option').text(font_style);
    //         this.$el.find('#engraveFontid span.filter-option').removeClass().addClass('filter-option pull-left').addClass(font_style);
    //         this.$engravingPreview.removeClass().addClass(font_style);
    //     }


    // });
});


