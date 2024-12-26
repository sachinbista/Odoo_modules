odoo.define('bista_warehouse_inventory.custom_tooltip', function (require) {

    var widgetRegistry = require('web.widget_registry');
    var fieldRegistry = require('web.field_registry');
    var FieldHtml = require('web_editor.field.html');


    var CustomTooltip = FieldHtml.extend({

        init: function (parent, options) {
            this._super.apply(this, arguments);
        },

        start: function () {
            this._super();
        },
        _renderReadonly: function () {
            this.$el.html(this.value);
            this.$el.addClass('zoom');
        },

    });

    fieldRegistry.add('custom_tooltip', CustomTooltip);

    return {
        CustomTooltip: CustomTooltip,
    };

});