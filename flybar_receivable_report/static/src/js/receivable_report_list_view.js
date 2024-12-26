odoo.define('flybar_receivable_report.ReceivableReportListView', function (require) {
"use strict";

var ListView = require('web.ListView');
var ReceivableReportListController = require('flybar_receivable_report.ReceivableReportListController');
var viewRegistry = require('web.view_registry');


var ReceivableReportListView = ListView.extend({
    config: _.extend({}, ListView.prototype.config, {
        Controller: ReceivableReportListController,
    }),
});

viewRegistry.add('receivable_report_list', ReceivableReportListView);

return ReceivableReportListView;

});
