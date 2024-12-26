odoo.define('flybar_payable_report.PayableReportListController', function (require) {
"use strict";

var ListController = require('web.ListController');
var BasicController = require('web.BasicController');
var core = require('web.core');
var _t = core._t;

var PayableReportListController = ListController.extend({
    buttons_template: 'PayableReport.Buttons',

    // -------------------------------------------------------------------------
    // Public
    // -------------------------------------------------------------------------

    custom_events: _.extend({}, ListController.prototype.custom_events, {
        value_clicked: '_onValueClicked',
    }),


    init: function (parent, model, renderer, params) {
        this.context = renderer.state.getContext();
        return this._super.apply(this, arguments);
    },

    /**
     * @override
     */
    renderButtons: function ($node) {
        this._super.apply(this, arguments);
        this.$buttons.on('click', '.o_button_run_payable', this._onRunReport.bind(this));
    },

    _onRunReport: function () {
        this.do_action({
            res_model: 'account.payable.report.wizard',
            views: [[false, 'form']],
            target: 'new',
            type: 'ir.actions.act_window',
        });
    },

});

return PayableReportListController;

});
