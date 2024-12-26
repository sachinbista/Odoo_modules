odoo.define('fds_multi_pricelist_report.generate_pricelist', function (require) {
'use strict';

const GeneratePriceList = require('product.generate_pricelist').GeneratePriceList;
var FieldMany2ManyTags = require('web.relational_fields').FieldMany2ManyTags;
var FieldMany2One = require('web.relational_fields').FieldMany2One;
var StandaloneFieldManagerMixin = require('web.StandaloneFieldManagerMixin');

GeneratePriceList.include({
    /**
     * @override
     */
    willStart: function () {
        let getPricelist;
        // started without a selected pricelist in context? just get the first one
        if (this.context.default_pricelist) {
            getPricelist = Promise.resolve([this.context.default_pricelist]);
        } else {
            getPricelist = this._rpc({
                model: 'product.pricelist',
                method: 'search',
                args: [[]],
                kwargs: {limit: 1}
            });
        }
        const fieldSetup = getPricelist.then(pricelistIds => {
            var self = this;
            return this._rpc({
                model: 'product.pricelist',
                method: 'name_get',
                args: pricelistIds,
            }).then(function (result) {
                const display_name = result[0][1];
                return self.model.makeRecord('report.product.report_pricelist', [
                    {
                        name: 'pricelist_id',
                        type: 'many2one',
                        relation: 'product.pricelist',
                        value: pricelistIds[0],
                    },
                    {
                        name: 'pricelist_ids',
                        type: 'many2many',
                        relation: 'product.pricelist',
                        value: [{id: pricelistIds[0], display_name: display_name}],
                    }
                ]);
            });
        }).then(recordID => {
            const record = this.model.get(recordID);
            this.many2one = new FieldMany2One(this, 'pricelist_id', record, {
                mode: 'edit',
                attrs: {
                    can_create: false,
                    can_write: false,
                    options: {no_open: true},
                },
            });
            this._registerWidget(recordID, 'pricelist_id', this.many2one);
            this.many2many = new FieldMany2ManyTags(this, 'pricelist_ids', record, {
                mode: 'edit',
                attrs: {
                    can_create: false,
                    can_write: false,
                    options: {no_open: true},
                },
            });
            this._registerWidget(recordID, 'pricelist_ids', this.many2many);
        });
        return Promise.all([fieldSetup, this._getHtml(), this._super()]);
    },
    _renderComponent: function () {
        const { $buttons, $searchview } = this._super();
        
        this.many2many.appendTo($searchview.find('.o_pricelists'));
        return { $buttons, $searchview };
    },
    /**
     * Reload report when pricelist changed.
     *
     * @override
     */
    _onFieldChanged: function (event) {
        if (event.data.changes.pricelist_id) {
            this.context.pricelist_id = event.data.changes.pricelist_id.id;
        }
        else if (event.data.changes.pricelist_ids) {
            this._onPricelistsChanged(event)
        }
        StandaloneFieldManagerMixin._onFieldChanged.apply(this, arguments);
        this._reload();
    },
    _onPricelistsChanged: function(event) {
        var current_ids = _.map(this.many2many.value.data, function (rec) {
            return {
                id: rec.id,
                res_id: rec.res_id
            };
        });
        const { operation, ids } = event.data.changes.pricelist_ids;
        if (operation === "ADD_M2M") {
            current_ids.push({id: '', res_id: ids.id})
        } else if (operation === "FORGET"){
            current_ids = _.reject(current_ids, function(el) { return el.id === ids[0]; });
        }
        const pricelist_ids = _.map(current_ids, function (rec) {
            return rec.res_id
        })
        if (!pricelist_ids.length) {
            console.log("Empty")
        }
        this.context.pricelist_ids = pricelist_ids;
    },
    _prepareActionReportParams: function () {
        var result = this._super();
        result.pricelist_ids = this.context.pricelist_ids || [];
        return result;
    },
});

});
