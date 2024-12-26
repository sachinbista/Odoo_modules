# -*- encoding: utf-8 -*-
##############################################################################
#
#    Bista Solutions Pvt. Ltd
#    Copyright (C) 2023 (http://www.bistasolutions.com)
#
##############################################################################

from odoo import models, fields, api, _, Command



class ProductTemplate(models.Model):
    _inherit = 'product.template'

    @api.onchange('brand_id')
    def set_brand_attribute_value(self):
        for record in self:
            if not record.brand_id:
                break
            attribute_ids = record.attribute_line_ids.filtered(lambda s: s.attribute_id and s.attribute_id.dr_is_brand and s.attribute_id.visibility=='visible')
            attribute_id = self.env['product.attribute'].search([('dr_is_brand','=',True),('visibility','=','visible')], limit=1)
            if not attribute_ids:
                value_ids = attribute_id.value_ids.filtered(lambda s: s.name == record.brand_id.name)
                if not value_ids:
                    product_attribute_value= self.env['product.attribute.value'].create({
                        'name': record.brand_id.name,
                        'attribute_id':  attribute_id.id,
                        'brand_id': record.brand_id.id
                        })
                    record.update({
                        'attribute_line_ids':[Command.create({
                             'attribute_id': attribute_id.id,
                             'value_ids': [fields.Command.link(product_attribute_value.id)]
                            })]
                        })

                else:
                    if value_ids:
                        record.update({
                        'attribute_line_ids':[Command.create({
                             'attribute_id': attribute_id.id,
                             'value_ids': [fields.Command.link(value_ids.id)]
                                })]
                        })
                        value_ids.update({
                            'brand_id': record.brand_id.id
                            })
                    else:
                        record.update({
                        'attribute_line_ids':[Command.create({
                             'attribute_id': attribute_id.id,
                             'value_ids': [fields.Command.link(value_ids.ids)]
                                })]
                        })
            else:
                value_ids = attribute_id.value_ids.filtered(lambda s: s.name == record.brand_id.name)
                if not value_ids:
                    product_attribute_value= self.env['product.attribute.value'].create({
                        'name': record.brand_id.name,
                        'attribute_id':  attribute_id.id,
                        'brand_id': record.brand_id.id
                        })
                    attribute_ids.update({
                         'value_ids': [fields.Command.link(product_attribute_value.id)]
                        })
                else:

                    attribute_ids.update({
                         'value_ids': [Command.set(x.id for x in value_ids)]
                        })
                    if not value_ids.brand_id:
                        value_ids.update({
                            'brand_id': record.brand_id.id
                            })