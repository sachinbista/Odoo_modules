odoo.define('flybar_payable_report.PayableReportListView', function (require) {
"use strict";

var ListView = require('web.ListView');
var PayableReportListController = require('flybar_payable_report.PayableReportListController');
var viewRegistry = require('web.view_registry');


var PayableReportListView = ListView.extend({
    config: _.extend({}, ListView.prototype.config, {
        Controller: PayableReportListController,
    }),
});

viewRegistry.add('payable_report_list', PayableReportListView);

return PayableReportListView;

});
