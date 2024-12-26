odoo.define('fds_payment_require.name_and_signature', function (require) {
    'use strict';

    var core = require('web.core');
    var config = require('web.config');
    var utils = require('web.utils');
    var Widget = require('web.Widget');
    var NameAndSignature = require('web.name_and_signature').NameAndSignature;


    /**
     * This widget allows the user to input his name and to draw his signature.
     * Alternatively the signature can also be generated automatically based on
     * the given name and a selected font, or loaded from an image file.
     */
    NameAndSignature.include({
        init: function (parent, options) {
            this._super.apply(this, arguments);
            options = options || {};
            this.htmlId = _.uniqueId();
            this.defaultName = options.defaultName || '';
            this.defaultPo = options.defaultPo || '';
            this.defaultFont = options.defaultFont || '';
            this.fontColor = options.fontColor || 'DarkBlue';
            this.displaySignatureRatio = options.displaySignatureRatio || 3.0;
            this.signatureType = options.signatureType || 'signature';
            // default mode should be auto except when noInputName is true and no default name
            this.signMode = options.mode || (options.noInputName && !this.defaultName ? 'draw' : 'auto');
            this.noInputName = options.noInputName || false;
            this.currentFont = 0;
            this.drawTimeout = null;
            this.drawPreviewTimeout = null;
            this.signatureAreaHidden = false;
        },
        start: function () {
            var self = this;
            // signature and name input
            this.$signatureGroup = this.$('.o_web_sign_signature_group');
            this.$signatureField = this.$('.o_web_sign_signature');
            this.$nameInput = this.$('.o_web_sign_name_input');
            this.$poInput = this.$('.o_web_sign_po_input');
            this.$('.o_web_sign_po_input').val(this.defaultPo);
            this.$nameInputGroup = this.$('.o_web_sign_name_group');
            this.$poInputGroup = this.$('.o_web_sign_po_group');

            // mode selection buttons
            this.$drawButton = this.$('a.o_web_sign_draw_button');
            this.$autoButton = this.$('a.o_web_sign_auto_button');
            this.$loadButton = this.$('a.o_web_sign_load_button');

            // mode: draw
            this.$drawClear = this.$('.o_web_sign_draw_clear');

            // mode: auto
            this.$autoSelectStyle = this.$('.o_web_sign_auto_select_style');
            this.$autoFontSelection = this.$('.o_web_sign_auto_font_selection');
            this.$autoFontList = this.$('.o_web_sign_auto_font_list');
            for (var i in this.fonts) {
                var $img = $('<img/>').addClass('img-fluid');
                var $a = $('<a/>').addClass('btn p-0').append($img).data('fontNb', i);
                this.$autoFontList.append($a);
            }

            // mode: load
            this.$loadFile = this.$('.o_web_sign_load_file');
            this.$loadInvalid = this.$('.o_web_sign_load_invalid');

            if (this.fonts && this.fonts.length < 2) {
                this.$autoSelectStyle.hide();
            }

            if (this.noInputName) {
                if (this.defaultName === "") {
                    this.$autoButton.hide();
                }
                this.$nameInputGroup.hide();
            } else if (this.defaultName === "") {
                this._hideSignatureArea();
            }

            // Resize the signature area if it is resized
            $(window).on('resize.o_web_sign_name_and_signature', _.debounce(function () {
                if (self.isDestroyed()) {
                    // May happen since this is debounced
                    return;
                }
                self.resizeSignature();
            }, 250));

            return this._super.apply(this, arguments);
        },
        /**
         * Gets the po currently given by the user.
         *
         * @returns {string} po
         */
        getPo: function () {
            return this.$poInput.val();
        },
    });
});
