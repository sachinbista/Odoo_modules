odoo.define('bista_sale_reports.account_report', function (require) {
    'use strict';
    var core = require('web.core');
    var RelationalFields = require('web.relational_fields');
    var StandaloneFieldManagerMixin = require('web.StandaloneFieldManagerMixin');
    var { WarningDialog } = require("@web/legacy/js/_deprecated/crash_manager_warning_dialog");
    var Widget = require('web.Widget');
    var accountReportsWidget = require('account_reports.account_report').accountReportsWidget;

    var QWeb = core.qweb;
    var _t = core._t;

    var M2MFilters = Widget.extend(StandaloneFieldManagerMixin, {
        /**
         * @constructor
         * @param {Object} fields
         */
        init: function (parent, fields, change_event) {
            this._super.apply(this, arguments);
            StandaloneFieldManagerMixin.init.call(this);
            this.fields = fields;
            this.widgets = {};
            this.change_event = change_event;
        },
        /**
         * @override
         */
        willStart: function () {
            var self = this;
            var defs = [this._super.apply(this, arguments)];
            _.each(this.fields, function (field, fieldName) {
                defs.push(self._makeM2MWidget(field, fieldName));
            });
            return Promise.all(defs);
        },
        /**
         * @override
         */
        start: function () {
            var self = this;
            var $content = $(QWeb.render("m2mWidgetTable", {fields: this.fields}));
            self.$el.append($content);
            _.each(this.fields, function (field, fieldName) {
                self.widgets[fieldName].appendTo($content.find('#'+fieldName+'_field'));
            });
            return this._super.apply(this, arguments);
        },

        //--------------------------------------------------------------------------
        // Private
        //--------------------------------------------------------------------------
        /**
         * This method will be called whenever a field value has changed and has
         * been confirmed by the model.
         *
         * @private
         * @override
         * @returns {Promise}
         */
        _confirmChange: function () {
            var self = this;
            var result = StandaloneFieldManagerMixin._confirmChange.apply(this, arguments);
            var data = {};
            _.each(this.fields, function (filter, fieldName) {
                data[fieldName] = self.widgets[fieldName].value.res_ids;
            });
            this.trigger_up(this.change_event, data);
            return result;
        },
        /**
         * This method will create a record and initialize M2M widget.
         *
         * @private
         * @param {Object} fieldInfo
         * @param {string} fieldName
         * @returns {Promise}
         */
        _makeM2MWidget: function (fieldInfo, fieldName) {
            var self = this;
            var options = {};
            options[fieldName] = {
                options: {
                    no_create_edit: true,
                    no_create: true,
                }
            };
            return this.model.makeRecord(fieldInfo.modelName, [{
                fields: [{
                    name: 'id',
                    type: 'integer',
                }, {
                    name: 'display_name',
                    type: 'char',
                }],
                name: fieldName,
                relation: fieldInfo.modelName,
                type: 'many2many',
                value: fieldInfo.value,
            }], options).then(function (recordID) {
                self.widgets[fieldName] = new RelationalFields.FieldMany2ManyTags(self,
                    fieldName,
                    self.model.get(recordID),
                    {mode: 'edit',}
                );
                self._registerWidget(recordID, fieldName, self.widgets[fieldName]);
            });
        },
    });


    accountReportsWidget.include({
        custom_events: _.extend({}, accountReportsWidget.prototype.custom_events, {
            'user_filter_changed': function (ev) {
                var self = this;
                self.report_options.users_ids = ev.data.user_ids;
                return self.reload().then(function () {
                    self.$searchview_buttons.find('.account_user_filter').click();
                });
            },

            'category_filter_changed': function(ev) {
                 var self = this;
                 self.report_options.category_ids = ev.data.category_ids;
                 return self.reload().then(function () {
                     self.$searchview_buttons.find('.account_product_category_filter').click();
                 });
            },

            'details_filter_changed': function(ev) {
                 var self = this;
                 self.report_options.locations_ids = ev.data.locations_ids;
                 return self.reload().then(function () {
                     self.$searchview_buttons.find('.account_locations_filter').click();
                 });
             },

            'sorting_filter_changed': function(ev) {
                 var self = this;
                 self.report_options.products_ids = ev.data.products_ids;
                 return self.reload().then(function () {
                     self.$searchview_buttons.find('.account_products_filter').click();
                 });
             },

            'customer_limit_filter_changed': function(ev) {
                 var self = this;
                 self.report_options.variants_ids = ev.data.variants_ids;
                 return self.reload().then(function () {
                     self.$searchview_buttons.find('.account_variants_filter').click();
                 });
             },
        }),

        render_searchview_buttons: function () {
            var self = this;
                _.each(this.$searchview_buttons.find('.js_account_report_choice_filter'), function(k) {
                $(k).toggleClass('selected', (_.filter(self.report_options[$(k).data('filter')], function(el){return ''+el.id == ''+$(k).data('id') && el.selected === true;})).length > 0);
            });
            this.$searchview_buttons.find('.js_account_report_choice_filter').click(function (event) {
            var option_value = $(this).data('filter');
            var option_id = $(this).data('id');

            // Deselect previously selected months
            _.each(self.report_options[option_value], function(el) {
                if (el.id != option_id && el.selected) {
                    el.selected = false;
                }
            });

            // Toggle the selected state of the clicked month
            _.filter(self.report_options[option_value], function(el) {
                if (''+el.id == ''+option_id){
                    if (el.selected === undefined || el.selected === null){el.selected = false;}
                    el.selected = !el.selected;
                }
                return el;
            });

            self.reload();
        });


            // User Many2many filter
            if (this.report_options.user) {
                if (!this.M2MFilters_Users) {
                    var fields = {};
                    if ('users_ids' in this.report_options) {
                        fields['user_ids'] = {
                            label: _t('Users'),
                            modelName: 'res.users',
                            value: this.report_options.users_ids.map(Number),
                        };
                    }
                    if (!_.isEmpty(fields)) {
                        this.M2MFilters_Users = new M2MFilters(this, fields, 'user_filter_changed');
                        this.M2MFilters_Users.appendTo(this.$searchview_buttons.find('.js_account_user_m2m'));
                    }
                } else {
                    this.$searchview_buttons.find('.js_account_user_m2m').append(this.M2MFilters_Users.$el);
                }
            }

            // Product Category Many2many filter
            if (this.report_options.category) {
                if (!this.M2MFilters_Category) {
                    var fields = {};
                    if ('category_ids' in this.report_options) {
                        fields['category_ids'] = {
                            label: _t('Categories'),
                            modelName: 'product.category',
                            value: this.report_options.category_ids.map(Number),
                        };
                    }
                    if (!_.isEmpty(fields)) {
                        this.M2MFilters_Category = new M2MFilters(this, fields, 'category_filter_changed');
                        this.M2MFilters_Category.appendTo(this.$searchview_buttons.find('.js_account_category_m2m'));
                    }
                }
                else {
                    this.$searchview_buttons.find('.js_account_category_m2m').append(this.M2MFilters_Category.$el);
                }
            }

            // Customer Limit handler and filter
            const customerLimitHandler = function (event) {
                let optionValue = $(this).data('filter');
                if (optionValue === 'customer_limit') {
                    _.each($('input.js_account_customer_limit_input'), (input) => {
                        self.report_options.customer_limit['limit'] = input.value;
                    });
                }
                self.reload();
            };
            $(document).on('click', '.js_account_report_customer_limit', customerLimitHandler);
            this.$searchview_buttons.find('.js_account_report_customer_limit').click(customerLimitHandler);
            self._super();
        },
    });
});
