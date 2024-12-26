##############################################################################
#
# Bista Solutions Pvt. Ltd
# Copyright (C) 2022 (http://www.bistasolutions.com)
#
##############################################################################
import logging
import time

from odoo import models, fields, api, _
from dateutil.relativedelta import relativedelta
from odoo.tools.safe_eval import safe_eval

_logger = logging.getLogger(__name__)


class ShopifyQueueJob(models.Model):
    _name = "shopify.queue.job"
    _inherit = ['mail.thread', 'mail.activity.mixin', 'portal.mixin']
    _description = 'Shopify Queue Job'
    _order = "id desc"

    @api.depends('shop_queue_line_ids.state')
    def _compute_queue_line_counts_and_state(self):
        """
           This method will compute the states
           and counts on the line of queues.
           @author: Ashwin Khodifad @Bista Solutions Pvt. Ltd.
       """
        for q_job in self:
            shop_queue_line_ids = q_job.shop_queue_line_ids
            if all(line.state == 'processed' or line.state == 'cancelled' for line in shop_queue_line_ids):
                q_job.state = 'processed'
            elif all(line.state == 'draft' for line in shop_queue_line_ids):
                q_job.state = 'draft'
            elif all(line.state == 'failed' for line in shop_queue_line_ids):
                q_job.state = 'failed'
            else:
                q_job.state = 'partial_processed'

    name = fields.Char('Name', readonly=True, index=True,
                       default=lambda self: _('New'))
    shopify_config_id = fields.Many2one('shopify.config', "Shopify Configuration",
                                        ondelete='cascade')
    operation_type = fields.Selection([('import_customer', 'Import Customer'),
                                       ('import_product', 'Import Product'),
                                       ('import_order_by_ids',
                                        'Import Order by IDs'),
                                       ('import_order', 'Import Orders'),
                                       ('import_refund', 'Import Refund'),
                                       ('import_return', 'Import Returns'),
                                       ('export_product', 'Export Product'),
                                       ('export_stock', 'Export Stock'),
                                       ('import_returns_refunds', 'Import Returns/Refunds')],
                                      string="Operation Type", required=True)
    state = fields.Selection([('draft', 'Draft'),
                              ('partial_processed', 'Partial Processed'),
                              ('processed', 'Processed'), ('failed', 'Failed')],
                             default='draft', string='Status',
                             compute='_compute_queue_line_counts_and_state',
                             store=True)
    shopify_log_id = fields.Many2one(
        'shopify.error.log', string="Shopify Logs")
    shop_queue_line_ids = fields.One2many("shopify.queue.job.line",
                                          "shop_queue_id", string="Queue Lines")
    webhook_queue = fields.Boolean('Is Webhook Queue?', default=False)

    def action_create_queue_lines(self, line_vals):
        """
            This method will create the queue lines.
            @author: Ashwin Khodifad @Bista Solutions Pvt. Ltd.
        """
        queue_job_line_obj = self.env['shopify.queue.job.line']
        existing_lines = self.env['shopify.queue.job.line'].sudo().search(
            [('shopify_id', '=', line_vals.get('shopify_id')),
             ('state', 'in', ['draft', 'failed']),
             ('shop_queue_id.operation_type', '=', self.operation_type)])
        if existing_lines:
            existing_lines.write({'state': 'cancelled'})
        if not line_vals:
            return self.env['shopify.queue.job.line']
        line_vals.update({'shop_queue_id': self.id})
        return queue_job_line_obj.create(line_vals)

    @api.model_create_multi
    def create(self, vals):
        for val in vals:
            if val.get('name', _('New')) == _('New'):
                val['name'] = self.env['ir.sequence'].sudo().next_by_code(
                    'shopify.queue.job') or _('New')
        return super().create(vals)

    def queue_process(self):
        """
            This method will process the queue
            based on operation type.
            @author: Ashwin Khodifad @Bista Solutions Pvt. Ltd.
        """
        self.ensure_one()
        shopify_log_id = self.shopify_log_id
        if not shopify_log_id:
            shopify_log_id = self.env['shopify.error.log'].sudo().create_update_log(
                shopify_config_id=self.shopify_config_id)
            self.shopify_log_id = shopify_log_id.id

        if self.operation_type == 'import_customer':
            shopify_log_id.update({'operation_type': 'import_customer'})
            self.import_shopify_customer_queue_process()
        elif self.operation_type == 'import_product':
            shopify_log_id.update({'operation_type': 'import_product'})
            self.import_shopify_product_queue_process()
        elif self.operation_type == 'import_order':
            shopify_log_id.update({'operation_type': 'import_order'})
            self.import_shopify_order_queue_process()
        elif self.operation_type == 'import_refund':
            shopify_log_id.update({'operation_type': 'import_refund'})
            self.import_shopify_refund_queue_process()
        elif self.operation_type == 'import_return':
            shopify_log_id.update({'operation_type': 'import_return'})
            self.import_shopify_return_queue_process()
        elif self.operation_type == 'import_returns_refunds':
            shopify_log_id.update({'operation_type': 'import_returns_refunds'})
            self.import_returns_refunds_on_one_click()

        if not shopify_log_id.shop_error_log_line_ids:
            shopify_log_id.unlink()
        return True

    def do_failed_queue_process(self):
        """
            This method will process the failed queue
            based on operation type.
            @author: Ashwin Khodifad @Bista Solutions Pvt. Ltd.
        """
        self.ensure_one()
        shopify_log_id = self.shopify_log_id
        if not shopify_log_id:
            shopify_log_id = self.env['shopify.error.log'].sudo().create_update_log(
                shopify_config_id=self.shopify_config_id)
            self.shopify_log_id = shopify_log_id.id

        if self.operation_type == 'import_customer':
            shopify_log_id.update({'operation_type': 'import_customer'})
            self.import_shopify_customer_failed_queue__process()
        elif self.operation_type == 'import_product':
            shopify_log_id.update({'operation_type': 'import_product'})
            self.import_shopify_product_failed_queue_process()
        elif self.operation_type == 'import_order':
            shopify_log_id.update({'operation_type': 'import_order'})
            self.import_shopify_order_failed_queue_process()
        elif self.operation_type == 'import_refund':
            shopify_log_id.update({'operation_type': 'import_refund'})
            self.import_shopify_refund_failed_queue_process()
        elif self.operation_type == 'import_return':
            shopify_log_id.update({'operation_type': 'import_return'})
            self.import_shopify_return_failed_queue_process()
        elif self.operation_type == 'import_returns_refunds':
            shopify_log_id.update({'operation_type': 'import_returns_refunds'})
            self.import_failed_returns_refunds_on_one_click()

        if not shopify_log_id.shop_error_log_line_ids:
            shopify_log_id.unlink()
        return True

    def import_shopify_customer_queue_process(self):
        """
            This method will create the
            shopify customer's process.
            @author: Ashwin Khodifad @Bista Solutions Pvt. Ltd.
        """
        res_partner_obj = self.env['res.partner'].sudo()
        draft_queue_line_ids = self.shop_queue_line_ids.filtered(
            lambda x: x.state == 'draft' or x.state == 'failed' or x.state == 'cancelled')
        for line in draft_queue_line_ids:
            customer_dict = safe_eval(line.record_data)
            res_partner_obj.with_context(queue_line_id=line,
                                         shopify_log_id=line.shop_queue_id.shopify_log_id).create_update_shopify_customers(
                customer_dict, self.shopify_config_id)
            line.write({'processed_date': fields.Datetime.now()})
        return True

    def import_shopify_customer_failed_queue__process(self):
        """
            This method will create the failed
            shopify customer's process.
            @author: Ashwin Khodifad @Bista Solutions Pvt. Ltd.
        """
        res_partner_obj = self.env['res.partner'].sudo()
        draft_queue_line_ids = self.shop_queue_line_ids.filtered(
            lambda x: x.state == 'failed' or x.state == 'draft' or x.state == 'cancelled')
        for line in draft_queue_line_ids:
            customer_dict = safe_eval(line.record_data)
            res_partner_obj.with_context(queue_line_id=line,
                                         shopify_log_id=line.shop_queue_id.shopify_log_id).create_update_shopify_customers(
                customer_dict, self.shopify_config_id)
            line.write({'processed_date': fields.Datetime.now()})
        return True

    def import_shopify_refund_queue_process(self):
        """
            This method will create the queue
            shopify refund's process.
            @author: Ashwin Khodifad @Bista Solutions Pvt. Ltd.
        """
        move_obj = self.env['account.move'].sudo()
        draft_queue_line_ids = self.shop_queue_line_ids.filtered(
            lambda x: x.state == 'draft' or x.state == 'cancelled' or x.state == 'failed')
        for line in draft_queue_line_ids:
            order_dict = safe_eval(line.record_data)
            # TODO: Improve code. sleep() should be called only when "Too Many requests" error is raised
            # Fix for error "Too Many requests". 2 calls per second is allowed
            time.sleep(1)
            move_obj.with_context(queue_line_id=line,
                                  shopify_log_id=line.shop_queue_id.shopify_log_id).create_update_shopify_refund(
                order_dict, self.shopify_config_id)
            line.write({'processed_date': fields.Datetime.now()})
        return True

    def import_shopify_refund_failed_queue_process(self):
        """
           This method will create the queue for failed
           shopify refund's process.
           @author: Ashwin Khodifad @Bista Solutions Pvt. Ltd.
       """
        move_obj = self.env['account.move'].sudo()
        draft_queue_line_ids = self.shop_queue_line_ids.filtered(
            lambda x: x.state == 'failed' or x.state == 'draft' or x.state == 'cancelled')
        for line in draft_queue_line_ids:
            order_dict = safe_eval(line.record_data)
            move_obj.with_context(queue_line_id=line,
                                  shopify_log_id=line.shop_queue_id.shopify_log_id).create_update_shopify_refund(
                order_dict, self.shopify_config_id)
            line.write({'processed_date': fields.Datetime.now()})
        return True

    def import_shopify_order_queue_process(self):
        """
            This method will create the queue for
            shopify orders's process.
            @author: Ashwin Khodifad @Bista Solutions Pvt. Ltd.
        """
        order_obj = self.env['sale.order'].sudo()
        self.shopify_config_id.check_connection()
        draft_queue_line_ids = self.shop_queue_line_ids.filtered(
            lambda x: x.state == 'draft' or x.state == 'failed' or x.state == 'cancelled')
        for line in draft_queue_line_ids:
            order_dict = safe_eval(line.record_data)
            order_obj.with_context(queue_line_id=line,
                                   shopify_log_id=line.shop_queue_id.shopify_log_id).create_update_shopify_orders(
                order_dict, self.shopify_config_id)
            line.write({'processed_date': fields.Datetime.now()})
        return True

    def import_returns_refunds_on_one_click(self):
        """
            This method will create the queue for
            shopify return  process.
            @author: Ashwin Khodifad @Bista Solutions Pvt. Ltd.
        """
        order_obj = self.env['sale.order'].sudo()
        move_obj = self.env['account.move'].sudo()
        self.shopify_config_id.check_connection()
        draft_queue_line_ids = self.shop_queue_line_ids.filtered(
            lambda x: x.state == 'draft' or x.state == 'failed' or x.state == 'cancelled')

        # Author : Yogeshwar Chaudhari
        # Date   : 21/12/23
        # Client dont want return document in odoo from shopify
        for line in draft_queue_line_ids:
            order_dict = safe_eval(line.record_data)
            line.write({'processed_date': fields.Datetime.now()})

            order_obj.with_context(queue_line_id=line, shopify_log_id=line.shop_queue_id.shopify_log_id).process_return_order(
                order_dict, self.shopify_config_id)

        for line in draft_queue_line_ids:
            order_dict = safe_eval(line.record_data)
            line.write({'processed_date': fields.Datetime.now()})
            time.sleep(1)
            move_obj.with_context(queue_line_id=line, shopify_log_id=line.shop_queue_id.shopify_log_id).create_update_shopify_refund(
                order_dict, self.shopify_config_id)

        return True

    def import_failed_returns_refunds_on_one_click(self):
        order_obj = self.env['sale.order'].sudo()
        move_obj = self.env['account.move'].sudo()
        self.shopify_config_id.check_connection()
        draft_queue_line_ids = self.shop_queue_line_ids.filtered(
            lambda x: x.state == 'draft' or x.state == 'failed' or x.state == 'cancelled')

        for line in draft_queue_line_ids:
            order_dict = safe_eval(line.record_data)
            line.write({'processed_date': fields.Datetime.now()})

            order_obj.with_context(queue_line_id=line, shopify_log_id=line.shop_queue_id.shopify_log_id).process_return_order(
                order_dict, self.shopify_config_id)

            time.sleep(1)

            move_obj.with_context(queue_line_id=line, shopify_log_id=line.shop_queue_id.shopify_log_id).create_update_shopify_refund(
                order_dict, self.shopify_config_id)

        return True

    def import_shopify_return_queue_process(self):
        """
           This method will create the queue for
           shopify return  process.
           @author: Ashwin Khodifad @Bista Solutions Pvt. Ltd.
       """
        order_obj = self.env['sale.order'].sudo()
        draft_queue_line_ids = self.shop_queue_line_ids.filtered(
            lambda x: x.state == 'draft' or x.state == 'failed' or x.state == 'cancelled')
        for line in draft_queue_line_ids:
            order_dict = safe_eval(line.record_data)
            order_obj.with_context(queue_line_id=line,
                                   shopify_log_id=line.shop_queue_id.shopify_log_id).process_return_order(
                order_dict, self.shopify_config_id)
            line.write({'processed_date': fields.Datetime.now()})
        return True

    def import_shopify_order_failed_queue_process(self):
        """
            This method will create the queue for
            shopify failed order  process.
            @author: Ashwin Khodifad @Bista Solutions Pvt. Ltd.
        """
        order_obj = self.env['sale.order'].sudo()
        self.shopify_config_id.check_connection()
        draft_queue_line_ids = self.shop_queue_line_ids.filtered(
            lambda x: x.state == 'failed' or x.state == 'draft' or x.state == 'cancelled')
        for line in draft_queue_line_ids:
            order_dict = safe_eval(line.record_data)
            order_obj.with_context(queue_line_id=line,
                                   shopify_log_id=line.shop_queue_id.shopify_log_id).create_update_shopify_orders(
                order_dict, self.shopify_config_id)
            line.write({'processed_date': fields.Datetime.now()})
        return True

    def import_shopify_return_failed_queue_process(self):
        """
           This method will create the queue for
           shopify return failed  process.
           @author: Ashwin Khodifad @Bista Solutions Pvt. Ltd.
       """
        order_obj = self.env['sale.order'].sudo()
        draft_queue_line_ids = self.shop_queue_line_ids.filtered(
            lambda x: x.state == 'failed' or x.state == 'draft' or x.state == 'cancelled')
        for line in draft_queue_line_ids:
            order_dict = safe_eval(line.record_data)
            order_obj.with_context(queue_line_id=line,
                                   shopify_log_id=line.shop_queue_id.shopify_log_id).process_return_order(
                order_dict, self.shopify_config_id)
            line.write({'processed_date': fields.Datetime.now()})
        return True

    def import_shopify_product_queue_process(self):
        """
            This method will process the product
            queue for the shopify.
            @author: Ashwin Khodifad @Bista Solutions Pvt. Ltd.
        """
        shop_product_template_obj = self.env['shopify.product.template']
        draft_queue_line_ids = self.shop_queue_line_ids.filtered(
            lambda x: x.state == 'draft' or x.state == 'failed' or x.state == 'cancelled')
        for line in draft_queue_line_ids:
            product_dict = safe_eval(line.record_data)
            shop_product_template_obj.with_context(queue_line_id=line,
                                                   shopify_log_id=line.shop_queue_id.shopify_log_id).create_update_shopify_product(
                product_dict, self.shopify_config_id)
            line.write({'processed_date': fields.Datetime.now()})
        return True

    def import_shopify_product_failed_queue_process(self):
        """
            This method will process the failed product
            queue for the shopify.
            @author: Ashwin Khodifad @Bista Solutions Pvt. Ltd.
        """
        shop_product_template_obj = self.env['shopify.product.template']
        draft_queue_line_ids = self.shop_queue_line_ids.filtered(
            lambda x: x.state == 'failed' or x.state == 'draft' or x.state == 'cancelled')
        for line in draft_queue_line_ids:
            product_dict = safe_eval(line.record_data)
            shop_product_template_obj.with_context(queue_line_id=line,
                                                   shopify_log_id=line.shop_queue_id.shopify_log_id).create_update_shopify_product(
                product_dict, self.shopify_config_id)
            line.write({'processed_date': fields.Datetime.now()})
        return True


class ShopifyQueueJobLine(models.Model):
    _name = "shopify.queue.job.line"
    _description = 'Shopify Queue Job Line'

    name = fields.Char(string="Name", required=True)
    shopify_id = fields.Char("Shopify ID", copy=False)
    state = fields.Selection([('draft', 'Draft'), ('processed', 'Processed'),
                              ("cancelled", "Cancelled"), ('failed', 'Failed')],
                             default='draft', string='Status')
    shop_queue_id = fields.Many2one("shopify.queue.job", string="Queue",
                                    ondelete='cascade')

    shopify_config_id = fields.Many2one(related='shop_queue_id.shopify_config_id',
                                        string='Shopify Configuration')
    processed_date = fields.Datetime("Processed At", readonly=True)
    record_data = fields.Text("Data", copy=False)
    order_id = fields.Many2one("sale.order", string="Order", copy=False,
                               default=False)
    product_id = fields.Many2one(
        "product.template", string="Product", copy=False)
    partner_id = fields.Many2one("res.partner", string="Customer", copy=False)
    refund_id = fields.Many2one("account.move", string="Refund", copy=False)
    log_line_ids = fields.One2many("shopify.error.log.line", "queue_job_line_id",
                                   string="Shopify Error Log Lines")
