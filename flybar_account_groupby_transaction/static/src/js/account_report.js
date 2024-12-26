odoo.define('flybar_account_groupby_transaction.account_report', function (require) {
    'use strict';

    var core = require('web.core');
    var RelationalFields = require('web.relational_fields');
    var Widget = require('web.Widget');
    var StandaloneFieldManagerMixin = require('web.StandaloneFieldManagerMixin');
    var accountReportsWidget = require('account_reports.account_report').accountReportsWidget;


    var QWeb = core.qweb;
    var _t = core._t;


    accountReportsWidget.include({

        render_searchview_buttons: function () {
            var self = this;
            self._super();

            // Add Class Select/Unselect on selected transaction_type filter to show check/uncheck
            _.each(this.$searchview_buttons.find('.js_account_report_choice_filter_transaction_type'), function(k) {
                $(k).toggleClass('selected', (_.filter(self.report_options[$(k).data('filter')], function(el){return ''+el.id == ''+$(k).data('id') && el.selected === true;})).length > 0);
            });

            _.each(this.$searchview_buttons.find('.js_account_report_choice_filter_transaction_type'), function(el) {
                var $el = $(el);
                var option_value = 'transaction_type_ids';
                var options = _.filter(self.report_options[option_value], function(item){
                    return item.model == $el.data('model') && item.id.toString() == $el.data('id');
                });
                if(options.length > 0){
                    let option = options[0];
                    if(option.selected){
                        el.classList.add('selected');
                    }else{
                        el.classList.remove('selected');
                    }
                }
            });

            // // Event onclick for transaction_type filter button to select/unselect
            this.$searchview_buttons.find('.js_account_report_choice_filter_transaction_type').click(function (event) {
                var option_value = 'transaction_type_ids';
                var option_id = $(this).data('id');
                _.filter(self.report_options[option_value], function(el) {
                    if (''+el.id == ''+option_id){
                        if (el.selected === undefined || el.selected === null){el.selected = false;}
                        el.selected = !el.selected;
                    } else if (option_value === 'ir_filters') {
                        el.selected = false;
                    }
                    return el;
                });
                self.reload();
            });

        },
    });
});
