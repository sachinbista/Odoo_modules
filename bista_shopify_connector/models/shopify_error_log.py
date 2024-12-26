##############################################################################
#
# Bista Solutions Pvt. Ltd
# Copyright (C) 2022 (http://www.bistasolutions.com)
#
##############################################################################

from odoo import models, fields, api, _


class ShopifyErrorLog(models.Model):
    _name = "shopify.error.log"
    _description = "Shopify Error Log"
    _order = 'write_date desc'

    name = fields.Char(string='Name', copy=False, index=True,
                       readonly=True, default=lambda self: _('New'))
    shopify_config_id = fields.Many2one('shopify.config', "Shopify Configuration",
                                        ondelete='cascade')
    shop_error_log_line_ids = fields.One2many("shopify.error.log.line",
                                              "shop_error_log_id",
                                              "Shopify Error Log Lines")
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
                                       ('update_order_status', 'Update Order Status')],
                                      string="Operation Type")

    def prepare_create_line_vals(self, shopify_log_line_dict, operation_type):
        """ This method is used to prepare log vals"""
        log_line_list = []
        log_line_vals_list = shopify_log_line_dict.get(operation_type, [])
        log_line_vals_list = log_line_vals_list and [dict(t) for t in {tuple(d.items(
        )) for d in log_line_vals_list}] or log_line_vals_list  # Remove duplicate key value dict.
        for log_dict in log_line_vals_list:
            log_dict.update({'state': operation_type})
            log_line_list.append((0, 0, log_dict))
        return log_line_list

    def create_update_log(self, shop_error_log_id=False, shopify_config_id=False, operation_type='', shopify_log_line_dict=None):
        """ This method create and update log"""
        if not shopify_config_id and shop_error_log_id:
            shopify_config_id = shop_error_log_id.shopify_config_id
        log_line_list = []
        operation_type = self.env.context.get('operation_type', operation_type)
        shopify_log_id = self.env.context.get(
            'log_id', False) if not shop_error_log_id else shop_error_log_id
        shopify_log_line_dict = shopify_log_line_dict or self.env.context.get(
            'shopify_log_line_dict', {})
        if shopify_log_line_dict:
            log_line_list.extend(self.prepare_create_line_vals(
                shopify_log_line_dict, 'error'))
        if not shopify_log_id:
            log_vals = {'shopify_config_id': shopify_config_id and shopify_config_id.id or False,
                        'operation_type': operation_type}
            if log_line_list:
                log_vals.update({'shop_error_log_line_ids': log_line_list})
            shopify_log_id = self.create(log_vals)
        else:
            shopify_log_id.write({'shop_error_log_line_ids': log_line_list})
        return shopify_log_id

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'shopify.error.log') or _('New')
        rtn_ids = super().create(vals_list)
        # for removed extra log
        # for rtn in rtn_ids:
        #     extra_log = self.search([('id', '!=', rtn.id)]).filtered(
        #         lambda l: not l.shop_error_log_line_ids)
        #     if extra_log:
        #         extra_log.unlink()
        return rtn_ids


class ShopifyErrorLogLine(models.Model):
    _name = "shopify.error.log.line"
    _description = "Shopify Error Log Line"
    _rec_name = 'error_message'
    _order = 'write_date desc'

    shop_error_log_id = fields.Many2one(
        "shopify.error.log", "Shopify Error Log")
    state = fields.Selection([('error', 'Error'), ('success', 'Success')],
                             string="Status")
    error_message = fields.Text("Message")
    shopify_config_id = fields.Many2one(
        related='shop_error_log_id.shopify_config_id',
        string='Shopify Configuration')
