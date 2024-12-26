odoo.define('flybar_receivable_report.ReceivableReportListController', function (require) {
"use strict";

var ListController = require('web.ListController');
var BasicController = require('web.BasicController');
var core = require('web.core');
var _t = core._t;

var ReceivableReportListController = ListController.extend({
    buttons_template: 'ReceivableReport.Buttons',

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
        this.$buttons.on('click', '.o_button_run_receivable', this._onRunReport.bind(this));
    },

    _onRunReport: function () {
        this.do_action({
            res_model: 'account.receivable.report.wizard',
            views: [[false, 'form']],
            target: 'new',
            type: 'ir.actions.act_window',
        });
    },

    _onValueClicked: function (ev) {
        var self = this
        var data = ev.data
        this._rpc({
                model: 'account.receivable.report',
                method: 'get_aml_ids',
                args: [data.record_id, data.fieldName, data.domain],
            }).then(function (ids) {
               self.do_action({
                    type: "ir.actions.act_window",
                    name: 'Account Move Line',
                    res_model: 'account.move.line',
                    views: [[false, 'list'], [false, 'form']],
                    view_mode: "list, form",
                    target: "current",
                    domain: [['id', 'in', ids]],
                });
            });
    },



});

return ReceivableReportListController;

});
