# -*- encoding: utf-8 -*-
##############################################################################
#
#    Bista Solutions Pvt. Ltd
#    Copyright (C) 2023 (http://www.bistasolutions.com)
#
##############################################################################

from odoo import models, fields, api, _


class ProductProduct(models.Model):
    _inherit = 'product.product'

    @api.model_create_multi
    def create(self, vals_list):
        res = super(ProductProduct, self).create(vals_list)
        if "create_product_template" not in self._context:
            spring_instance_obj = self.env['spring.systems.configuration'].search([])
            if spring_instance_obj.sync_product:
                res.product_tmpl_id.with_context(create_springsystem_product=True).export_springsystem_product(
                    spring_instance_obj, res, vals_list)
        return res

    def update_spring_product(self, spring_instance_obj, res, vals=None, catalog_id=None):
        if catalog_id:
            spring_product_id = catalog_id[0].product_external_id
            connection_url = (spring_instance_obj.url + 'catalog-incoming/send' + '/api_user/' +
                              spring_instance_obj.api_user + '/api_key/' + spring_instance_obj.api_key + '/po.filter.gt.po_created/2017-09-01T00:00:00Z')
            payload = {
                "product_id": spring_product_id,
                "product_gtin": res.barcode,
                "product_vendor_item_num": res.default_code,
                "product_group_description": res.name,
                "default_cost": res.standard_price,
                "default_price": res.list_price}
            spring_instance_obj._send_spring_request("post", connection_url, payload=payload)
        return

    def write(self, values):
        self.product_tmpl_id._sanitize_vals(values)
        res = super(ProductProduct, self).write(values)
        if values and 'standard_price' or 'list_price' or 'name' in values:
            spring_instance_obj = self.env['spring.systems.configuration'].search([])
            if spring_instance_obj.sync_product:
                odoo_product_id = self.env['spring.system.product'].search(
                    [('product_id', '=', self.id)])
                self.update_spring_product(spring_instance_obj, self, values, odoo_product_id)
        return res


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    @api.model_create_multi
    def create(self, vals_list):
        res = super(ProductTemplate, self.with_context(create_product_template=True)).create(vals_list)
        if "create_product_product" not in self._context:
            spring_instance_obj = self.env['spring.systems.configuration'].search([])
            if spring_instance_obj.sync_product:
                self.export_springsystem_product(spring_instance_obj, res, vals_list)
        return res

    def export_springsystem_product(self, spring_instance, res, vals=None):
        if res:
            domain = []
            odoo_product_id = False
            if res.product_variant_id:
                domain.append(('product_id', '=', res.product_variant_id.id))
            if domain:
                odoo_product_id = self.env['spring.system.product'].search(
                    [('product_id', '=', res.product_variant_id.id)])
            if not odoo_product_id:
                self.create_springsystem_product(spring_instance, res)

    def create_springsystem_product(self, spring_instance, res):
        spring_product_vals = {}
        uom_abbr = ""
        if res.uom_id:
            uom_name = res.uom_id.name
            uom_abbr = 'EA' if uom_name == 'Units' else uom_name
        vals = {
            "catalog": {
                "product": [
                    {
                        "product_gtin": res.barcode,
                        "product_vendor_item_num": res.default_code,
                        "product_uom": uom_abbr,
                        "product_group": {
                            "product_group_description": res.name,
                            "product_additional": {
                                "identifiers": {
                                    "gtin": res.barcode,
                                    "vendor_item_num": res.default_code
                                },
                                "attributes": {
                                    "description": res.name
                                }
                            }
                        }
                    }
                ]
            }
        }
        text = ''
        if res.default_code:
            spring_product_vals.update(vals)
        else:
            text = 'Please Add product reference number to push on Spring'

        spring_product_obj = self.env['spring.system.product']
        config_id = spring_instance
        connection_url = (config_id.url + 'catalog-incoming/send' + '/api_user/' +
                          config_id.api_user + '/api_key/' + config_id.api_key)
        spring_connection_obj = config_id._send_spring_request("post", connection_url, payload=spring_product_vals)
        spring_product_id = False
        product_list = []
        if spring_connection_obj and spring_connection_obj.status_code == 200:
            spring_product_json = spring_connection_obj.json()
            product_list = spring_product_json.get('catalog', {}).get('product', [])
            if product_list:
                spring_product_id = product_list[0].get('product_id', False)
            else:
                spring_product_id = None
        else:
            text += '\n Product not created in Spring System.'
        spring_product_obj.create({'product_id': res.product_variant_id.id,
                                   'name': res.name,
                                   'item_number': res.default_code,
                                   'type': 'standard',
                                   'status': 'active' if res.active else 'inactive',
                                   'configuration_id': spring_instance.id,
                                   'info': text,
                                   'create_update_in_spring_system': True,
                                   'product_external_id': spring_product_id,
                                   'data': product_list
                                   })
