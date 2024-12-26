##############################################################################
#
# Bista Solutions Pvt. Ltd
# Copyright (C) 2022 (http://www.bistasolutions.com)
#
##############################################################################

from odoo import models, fields


class ShopifyLogLine(models.Model):
    _name = "shopify.log.line"
    _description = "Shopify Log Line"
    _rec_name = 'message'
    _order = 'write_date desc'

    name = fields.Char('Name')
    operation_type = fields.Selection([('import_customer', 'Import Customer'),
                                       ('import_product', 'Import Product'),
                                       ('import_order_by_ids',
                                        'Import Order by IDs'),
                                       ('import_order', 'Import Orders'),
                                       ('import_location', 'Import Location'),
                                       ('import_stock', 'Import Stock'),
                                       ('import_collection', 'Import Collection'),
                                       ('export_collection', 'Export Collection'),
                                       ('export_product', 'Export Product'),
                                       ('export_stock', 'Export Stock'),
                                       ('export_refund', 'Export Refund'),
                                       ('import_refund', 'Import Refund'),
                                       ('import_return', 'Import Returns'),
                                       ('update_order_status', 'Update Order '
                                                               'Status'),
                                       ('update_collection', 'Update '
                                                             'Collection'),
                                       ('update_product', 'Update Product')],
                                      string="Operation Type")
    state = fields.Selection([('error', 'Error'), ('success', 'Success'), ('pending', 'Pending')], default='pending',
                             string="Status")
    message = fields.Text("Message")
    shopify_config_id = fields.Many2one('shopify.config', "Shopify Configuration",
                                        ondelete='cascade')
    id_shopify = fields.Char('Shopify ID')
    related_model_name = fields.Char('Related Record model')
    related_model_id = fields.Char('Related Model ID')

    parent_id = fields.Many2one('shopify.log.line', string="Parent")
    log_lines_id = fields.One2many('shopify.log.line', 'parent_id', string="Record Log lines")


    def view_related_record(self):
        list_of_ids = self.related_model_id.split(',')
        action = {
            'name': 'Model Records',
            'type': 'ir.actions.act_window',
            'res_model': self.related_model_name,
            'view_mode': 'tree,form',
            'domain': [('id', 'in', list_of_ids)],
        }
        return action

