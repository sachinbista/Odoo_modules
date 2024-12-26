odoo.define('flybar_receivable_report.ReceivableReportListRenderer', function (require) {
"use_strict";

var config = require('web.config');
var field_utils = require('web.field_utils');
const ListRenderer = require('web.ListRenderer');
var core = require('web.core');
var _t = core._t;

ListRenderer.include({

    _renderAggregateCells: function (aggregateValues) {
        var self = this;

        return _.map(this.columns, function (column) {
            var $cell = $('<td>');
            if (config.isDebug()) {
                $cell.addClass(column.attrs.name);
            }
            if (column.attrs.editOnly) {
                $cell.addClass('oe_edit_only');
            }
            if (column.attrs.readOnly) {
                $cell.addClass('oe_read_only');
            }
            if (column.attrs.name in aggregateValues) {
                var field = self.state.fields[column.attrs.name];
                var value = aggregateValues[column.attrs.name].value;
                var help = aggregateValues[column.attrs.name].help;
                var formatFunc = field_utils.format[column.attrs.widget];
                if (!formatFunc) {
                    formatFunc = field_utils.format[field.type];
                }
                var formattedValue = formatFunc(value, field, {
                    escape: true,
                    digits: column.attrs.digits ? JSON.parse(column.attrs.digits) : undefined,
                });

                if (value && self.state.model == "account.receivable.report" && !('is_footer' in aggregateValues)) {
                    var $button = $('<button>')
                    .text(formattedValue)
                    .click(function(event) {
                        var group = $(event.currentTarget).closest('tr').data('group')
                        self.trigger_up('value_clicked', {
                            fieldName: $(event.currentTarget).data('fieldName'),
                            record_id: group.id,
                            domain: group.domain,
                        });
                    });
                    $button[0].style.cssText = "background: none;border: none;padding: 0;color: #01666b;";
                    $button.data('fieldName', field.name);
                $cell.append($button);
                $cell.addClass('o_list_number').attr('title', help)
                } else {
                    $cell.addClass('o_list_number').attr('title', help).html(formattedValue);
                }
            }
            return $cell;
        });
    },

    _renderFooter: function () {
        var aggregates = {};
        _.each(this.columns, function (column) {
            if ('aggregate' in column) {
                aggregates[column.attrs.name] = column.aggregate;
            }
        });
        aggregates['is_footer'] = true
        var $cells = this._renderAggregateCells(aggregates);
        if (this.hasSelectors) {
            $cells.unshift($('<td>'));
        }
        return $('<tfoot>').append($('<tr>').append($cells));
    },

});

});