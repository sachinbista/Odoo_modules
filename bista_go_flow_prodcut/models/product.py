# -*- coding: utf-8 -*-
import json

from odoo import models, fields, api, _


class ProductProduct(models.Model):
    _inherit = 'product.product'

    @api.model_create_multi
    def create(self, vals_list):
        res = super(ProductProduct, self).create(vals_list)
        if "create_product_template" not in self._context and not 'create_from_goflow' in self._context:
            go_flow_instance_obj = self.env['goflow.configuration'].search([('active', '=', True), ('state', '=', 'done')], limit=1)
            for go_flow_instance in go_flow_instance_obj:
                if go_flow_instance.sync_product:
                    res.product_tmpl_id.with_context(create_goflow_product=True).export_goflow_product(go_flow_instance,
                                                                                                       res, vals_list)
        return res

    def update_goflow_product(self, go_flow_instance, res, vals=None, catalog_id=None):
        if catalog_id:
            go_flow_product_id = catalog_id[0].product_external_id
            url = '/v1/products/%s/pricing' % go_flow_product_id
            payload = {
                "default_cost": res.standard_price,
                "default_price": res.list_price}
            go_flow_instance._send_goflow_request("patch", url, payload=payload)
        return

    def write(self, values):
        self.product_tmpl_id._sanitize_vals(values)
        res = super(ProductProduct, self).write(values)
        context = self._context
        if self.id and not "create_product_product" in context and not 'create_from_goflow' in context and not 'create_product_template' in context:
            if values and ('standard_price' or 'list_price') in values and not '__last_update' in values:
                go_flow_instance_obj = self.env['goflow.configuration'].search([('active', '=', True), ('state', '=', 'done')], limit=1)
                for go_flow_instance in go_flow_instance_obj:
                    if go_flow_instance.sync_product:
                        odoo_product_id = self.env['goflow.product'].search(
                            [('product_id', '=', self.id)])
                        self.update_goflow_product(go_flow_instance, self, values, odoo_product_id)
        # if 'seller_ids' in values:
        #     for seller in values['seller_ids']:
        #         vendor_details = seller[2]
        #         seller_id = self.seller_ids.filtered(lambda x: x.id == seller[1])
        #         if vendor_details:
        #             go_flow_vendor = self.env['goflow.vendor'].search([('partner_id','=',vendor_details.get('partner_id', False) if vendor_details.get('partner_id', False) else self.id)])
        #             if go_flow_vendor:
        #                 self.create_goflow_vendor_product(vendor_details,go_flow_vendor)
        return res

    # def create_goflow_vendor_product(self, vendor_details, go_flow_vendor):
    #     go_flow_instance = self.env['goflow.configuration'].search([('state', '=', 'draft'), ('sync_purchase_order', '=', True)])
    #     dt = False
    #     if vendor_details.get('date_start', False):
    #         dt = datetime.strptime(vendor_details['date_start'], "%Y-%m-%d")
    #         dt.replace(tzinfo=utc)
    #     payload = {
    #       "other_products": "ignore",
    #       "ignore_other_products_on_error": bool(True),
    #       "inventory_expires_at": str(dt) if dt else '',
    #       "requests": [
    #         {
    #           "vendor_item_number": self.default_code,
    #           "mapped_product_id": 0,
    #           "inventory": {
    #             "quantity": int(vendor_details['min_qty'])
    #           },
    #           "cost": {
    #             "amount": int(vendor_details['price'])
    #           }
    #         }
    #       ]
    #     }
    #
    #     url = ('v1/vendors/%s/products/feeds' % go_flow_vendor.goflow_vendor_id)
    #     response = go_flow_instance._send_goflow_request('post', url , payload)
    #     if response:
    #         response = response.json()
    #         pass


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    brand = fields.Many2one('product.brand', string="Brand")
    manufacturer = fields.Many2one('product.manufacturer', string="Manufacturer")
    customs_description = fields.Html(
        'Description On Custom Forms', translate=True)
    condition = fields.Selection(
        [('new', 'New'),
         ('refurbished', 'Refurbished'),
         ('unknown', 'Unknown'),
         ('used', 'Used'), ],
        store=True, readonly=False)
    is_perishable = fields.Boolean(string='Is Perishable')
    parent_default_code = fields.Char("Parent Internal Ref.", copy=False)

    @api.model_create_multi
    def create(self, vals_list):
        res = super(ProductTemplate, self.with_context(create_product_template=True)).create(vals_list)
        if "create_product_product" not in self._context and not 'create_from_goflow' in self._context:
            go_flow_instance_obj = self.env['goflow.configuration'].search([('active', '=', True), ('state', '=', 'done')], limit=1)
            for go_flow_instance in go_flow_instance_obj:
                if go_flow_instance.sync_product:
                    self.export_goflow_product(go_flow_instance, res, vals_list)
        return res

    def export_goflow_product(self, go_flow_instance, res, vals=None):
        if res:
            domain = []
            odoo_product_id = False
            if res.product_variant_id:
                domain.append(('product_id', '=', res.product_variant_id.id))
            if domain:
                odoo_product_id = self.env['goflow.product'].search([('product_id', '=', res.product_variant_id.id)])
            if not odoo_product_id:
                self.create_goflow_product(go_flow_instance, res)

    def create_goflow_product(self, go_flow_instance, res):
        goflow_product_vals = {}
        # Mapping conditions to their corresponding values
        condition_mapping = {
            'new': 'New',
            'refurbished': 'Refurbished',
            'unknown': 'Unknown',
            'used': 'Used'
        }
        # Collecting details in a dictionary
        vals = {
            'details': {
                "name": res.name,
                "description": res.description or '',
                "category": res.categ_id.name or '',
                "brand": res.brand.name or '',
                "manufacturer": res.manufacturer.name or '',
                "condition": condition_mapping.get(res.condition, ''),
                'is_perishable': res.is_perishable
            },
            'customs': self._get_customs_vals(res),
            'pricing': self._get_pricing_vals(res),
            'settings': {
                "is_sellable": res.sale_ok,
                "is_purchasable": res.purchase_ok,
            },
            'shipping': self._get_shipping_vals(res),
            'identifiers': self.get_identifiers(self,res),
            "type": 'standard' if res.id else '',
            "item_number": res.default_code
        }
        goflow_product_vals.update(vals)
        text = 'Please Add product reference number to push on GoFlow'

        # units_of_measure = {}
        # if res.uom_id:
        #     uom_name = res.uom_id.name
        #     uom_abbr = 'EA' if uom_name == 'Units' else uom_name
        #     all = [{
        #         "quantity": int(res.uom_id.ratio),
        #         "abbreviation": uom_abbr
        #     }]
        #     if all:
        #         units_of_measure.update({'all': all})
        # goflow_product_vals.update({'units_of_measure': units_of_measure})
        goflow_product_obj = self.env['goflow.product']
        product_url = '/v1/products'
        config_id = go_flow_instance
        goflow_connection_obj = config_id._send_goflow_request("post", product_url, payload=goflow_product_vals)
        goflow_product_id = False
        if goflow_connection_obj and goflow_connection_obj.status_code == 201:
            goflow_product_json = goflow_connection_obj.json()
            goflow_product_id = goflow_product_json.get('id', False)
        else:
            text += '\n Product not created in Goflow.'
        goflow_product_obj.create({'product_id': res.product_variant_id.id,
                                   'name': res.name,
                                   'item_number': res.default_code,
                                   'type': 'standard',
                                   'status': 'active' if res.active else 'inactive',
                                   'configuration_id': go_flow_instance.id,
                                   'info': text,
                                   'create_update_in_goflow': True,
                                   'product_external_id': goflow_product_id,
                                   'data': goflow_product_vals})

    # def update_goflow_product(self, go_flow_instance, res, vals=None, catalog_id=None):
    #     return

    def _get_customs_vals(self, res):
        customs = {
            "hts_tariff_code": res.hs_code or '',
            "description": res.customs_description or ''
        }
        if res.country_of_origin:
            customs.update({"country_of_origin": res.country_of_origin.code.lower()})
        return customs

    def _get_pricing_vals(self, res):
        pricing_vals = {}
        if res.standard_price:
            pricing_vals.update({"default_cost": res.standard_price or 0.0})
        if res.list_price:
            pricing_vals.update({"default_price": res.list_price or 0.0})
        return pricing_vals

    def _get_shipping_vals(self, res):
        shipping_vals = {}
        weight_vals = {}
        dimensions_vals = {}
        if res.weight:
            weight_vals.update({
                "measure": "pounds",
                "amount": res.weight})
        if res.product_length and res.product_width and res.product_height:
            dimensions_vals.update({
                "measure": "inches",
                "length": res.product_length,
                "width": res.product_width,
                "height": res.product_height
            })
        if weight_vals:
            shipping_vals.update({"weight": weight_vals})
        if dimensions_vals:
            shipping_vals.update({"dimensions": dimensions_vals})
        return shipping_vals


    def get_identifiers(self, res, vals=None):
        identifiers = []
        if res and res.packaging_ids:
            for packaging in res.packaging_ids:
                if packaging.goflow_identifier_type and packaging.goflow_identifier_value:
                    identifiers.append({
                        "type": packaging.goflow_identifier_type or '',
                        "value": packaging.goflow_identifier_value or '',
                        # "unit_of_measure_id": goflow_identifier_uom_id
                    })
        return identifiers

    def sync_to_goflow(self):
        go_flow_instance_obj = self.env['goflow.configuration'].search([('active', '=', True), ('state', '=', 'done')], limit=1)
        if go_flow_instance_obj and go_flow_instance_obj.sync_product:
            for rec in self:
                self.export_goflow_product(go_flow_instance_obj, rec)




class ProductPackaging(models.Model):
    _inherit = "product.packaging"

    goflow_identifier_type = fields.Char(string="Identifier Type")
    goflow_identifier_value = fields.Char(string="Identifier Value")
    goflow_identifier_uom_id = fields.Char()
