odoo.define('bista_zpl_labels.form_controller_view_switch', function (require) {
    "use strict";

    var FormController = require('web.FormController');

    console.log("Loaded form controller ");
    FormController.include({
        init: function () {
            console.log("Form init ", this)
            this._super.apply(this, arguments);
        },
        _onSwitchView: function (event) {
            var self = this;
            var res_id = self.renderer.state.res_id;
            event.data.res_id = res_id
            event.data.currentId = res_id
            this._super.apply(this, arguments);
        },
    });
});