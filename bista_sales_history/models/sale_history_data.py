# -*- encoding: utf-8 -*-
##############################################################################
#
# Bista Solutions Pvt. Ltd
# Copyright (C) 2023 (https://www.bistasolutions.com)
#
##############################################################################

from odoo import api, fields, models, _
from odoo.osv import expression
from odoo.exceptions import ValidationError, UserError


class SaleHistoryData(models.Model):
    _name = "sale.history.data"
    _description = 'Sales History Data'
    _rec_name = 'sale_order_date'
    _order = 'invoice_date desc'

    def name_get(self):
        context = self._context
        res = []
        for history_data in self:
            name = ''
            contact_reference = history_data.contact_reference
            contact_name = history_data.contact_name
            if contact_reference:
                name += '[%s]' % (contact_reference)
            if contact_name:
                name += '%s' % (contact_name)
            res.append((history_data.id, name))
        return res

    contact_reference = fields.Char(string="Contact Reference", copy=False)
    contact_name = fields.Char(string="Contact Name", copy=False)
    customer_id = fields.Many2one('res.partner', string='Customer Link', copy=False)
    customer_reference_no = fields.Char(string="Customer Order #", copy=False)
    sales_obtain = fields.Selection([
        ('manual', 'Manual'),
        ('go_flow', 'Go Flow'),
        ('spring_system', 'Spring System'),
        ('market_time', 'Market Time')
    ], string="Order Obtain", copy=False)
    sale_order_no = fields.Char(string="Order No.", copy=False)
    sale_order_date = fields.Date(string="Order Date", copy=False)
    warehouse_name = fields.Char(string="Warehouse", copy=False)
    invoice_number = fields.Char(string="Invoice", copy=False)
    invoice_date = fields.Date(string="Invoice Date", copy=False)
    invoice_id = fields.Many2one('account.move', string='Invoice Link', copy=False)

    # One2many
    sale_lines_o2m = fields.One2many('sale.history.line', 'history_data_link',
                                     string='Sale History Lines', copy=False)
    note = fields.Text(string="Note", copy=False)
    user_id = fields.Many2one('res.users', string="Salesperson")


class Sale_History_Line(models.Model):
    _name = "sale.history.line"
    _description = "Sale History Line"
    _order = 'invoice_date desc'

    # Many2one
    so_line_id = fields.Many2one('sale.order.line', string='SO Line', copy=False)
    product_pricelist_item_id = fields.Many2one('product.pricelist.item', string='Pricelist Item', copy=False)
    history_data_link = fields.Many2one("sale.history.data", copy=False, ondelete='cascade', string="History ID")

    # Copied Fields from sale.history.line
    company_id = fields.Many2one('res.company', string='Company', copy=False)
    customer_id = fields.Many2one('res.partner', string='Customer Link', copy=False)
    product_id = fields.Many2one('product.product', string='Product Link', copy=False)
    invoice_id = fields.Many2one('account.move', string='Invoice Link', copy=False)
    product_name = fields.Char('Product', copy=False)
    name = fields.Char(string='Description', copy=False)
    product_uom_qty = fields.Float(string='Quantity', digits='Product Unit of Measure', default=1.0, copy=False)
    price_unit = fields.Monetary('Unit Price', default=0.0, copy=False)
    cost_price_unit = fields.Monetary('Cost', default=0.0, copy=False)
    price_subtotal = fields.Monetary('Extended Price', default=0.0, copy=False)
    cost_subtotal = fields.Monetary('Extended Cost', default=0.0, copy=False)

    invoice_item_no = fields.Char(string="Item Number", copy=False)
    inventory_product_categ = fields.Char(string="Product Category", copy=False)

    currency_id = fields.Many2one("res.currency", copy=False)
    # Related
    contact_reference = fields.Char(related="history_data_link.contact_reference", string="Contact Reference",
                                    store=True)
    contact_name = fields.Char(related="history_data_link.contact_name", string="Contact Name", store=True)
    customer_reference_no = fields.Char(related="history_data_link.customer_reference_no", string="Customer Order #",
                                        store=True)
    sales_obtain = fields.Selection(related="history_data_link.sales_obtain", string="Sales Obtain", store=True)
    sale_order_no = fields.Char(related="history_data_link.sale_order_no", string="Sales Order No.", store=True)
    sale_order_date = fields.Date(related="history_data_link.sale_order_date", string="Sale Order Date", copy=False,
                                  store=True)
    invoice_number = fields.Char(related="history_data_link.invoice_number", string="Invoice", store=True)
    invoice_date = fields.Date(related="history_data_link.invoice_date", string="Invoice Date", copy=False, store=True)
    user_id = fields.Many2one('res.users', string="Salesperson")
    new_user_id = fields.Many2one(related="customer_id.user_id", string="Current Salesperson", copy=False, store=True)
    is_shipping = fields.Boolean(string="Is Shipping")
    note = fields.Text(string="Note", copy=False)

    def show_inovice(self):
        invoice_id = self.invoice_id
        if invoice_id:
            return {
                'type': 'ir.actions.act_window',
                'name': 'Invoice',
                'view_mode': 'form',
                'res_model': 'account.move',
                'res_id': invoice_id.id,
                'target': 'current',
                'context': self._context.copy()
            }
        else:
            raise ValidationError(_('Invoice not found!'))

    def name_get(self):
        context = self._context
        res = []
        for history_line in self:
            if context.get('product_name'):
                product_name = history_line.product_name
                if product_name:
                    inventory_short_vendor_name = history_line.inventory_short_vendor_name
                    if inventory_short_vendor_name:
                        product_name = '%s[%s]' % (product_name, inventory_short_vendor_name)
                    res.append((history_line.id, product_name))
            elif context.get('contact_reference'):
                contact_reference = history_line.contact_reference
                contact_name = history_line.contact_name
                name = ''
                if contact_reference:
                    name += '[%s]' % (contact_reference)
                if contact_name:
                    name += '%s' % (contact_name)
                res.append((history_line.id, name or ''))
            elif context.get('vin'):
                vin_sn = history_line.vehicle_identification_number
                res.append((history_line.id, vin_sn or ''))
            elif context.get('unit'):
                vehicle_unit_no = history_line.vehicle_unit_no
                if vehicle_unit_no:
                    contact_reference = history_line.contact_reference
                    contact_name = history_line.contact_name
                    name = ''
                    if contact_reference:
                        name += '[%s]' % (contact_reference)
                    if contact_name:
                        name += '%s' % (contact_name)
                    res.append((history_line.id, '%s - %s' % (vehicle_unit_no, name) or ''))
            else:
                res.append((history_line.id, history_line.product_name))
        return res

    @api.model
    def _name_search(self, name, args=None, operator='ilike', limit=0, name_get_uid=None):
        args = args or []
        domain, ids_to_show = [], []
        context = self._context
        cr = self._cr
        if context.get('product_name'):
            if name:
                args += [('product_name', operator, name)]
            cr.execute("select max(id) from sale_history_line where product_name is not null group by product_name, inventory_short_vendor_name")
            ids_to_show = list(filter(None, map(lambda x: x[0], cr.fetchall())))
        elif context.get('contact_reference'):
            if name:
                args += ['|', ('contact_reference', operator, name), ('contact_name', operator, name)]
            cr.execute(
                "select max(id) from sale_history_line where contact_reference is not null group by contact_reference")
            ids_to_show = list(filter(None, map(lambda x: x[0], cr.fetchall())))
        domain = [('id', 'in', ids_to_show)]
        return self._search(expression.AND([domain, args]), limit=limit, access_rights_uid=name_get_uid)

    @api.model
    @api.returns('self',
                 upgrade=lambda self, value, args, offset=0, limit=None, order=None,
                                count=False: value if count else self.browse(value),
                 downgrade=lambda self, value, args, offset=0, limit=None, order=None,
                                  count=False: value if count else value.ids)
    def search(self, args, offset=0, limit=None, order=None, count=False):
        context = self._context
        cr = self._cr
        if context.get('product_name'):
            cr.execute("select max(id) from sale_history_line where product_name is not null group by product_name, inventory_short_vendor_name")
            ids_to_show = list(filter(None, map(lambda x: x[0], cr.fetchall())))
            args += [('id', 'in', ids_to_show)]
        elif context.get('contact_reference'):
            cr.execute(
                "select max(id) from sale_history_line where contact_reference is not null group by contact_reference")
            ids_to_show = list(filter(None, map(lambda x: x[0], cr.fetchall())))
            args += [('id', 'in', ids_to_show)]
        elif context.get('sales_person_mismatch'):
            cr.execute("select id from sale_history_line where user_id != new_user_id")
            ids_to_show = list(filter(None, map(lambda x: x[0], cr.fetchall())))
            args += [('id', 'in', ids_to_show)]
        return super(Sale_History_Line, self).search(args, offset, limit, order, count)

    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        context = self._context
        cr = self._cr
        if context.get('product_name'):
            cr.execute("select max(id) from sale_history_line where product_name is not null group by product_name, inventory_short_vendor_name")
            ids_to_show = list(filter(None, map(lambda x: x[0], cr.fetchall())))
            domain += [('id', 'in', ids_to_show)]
        elif context.get('contact_reference'):
            cr.execute(
                "select max(id) from sale_history_line where contact_reference is not null group by contact_reference")
            ids_to_show = list(filter(None, map(lambda x: x[0], cr.fetchall())))
            domain += [('id', 'in', ids_to_show)]
        elif context.get('sales_person_mismatch'):
            cr.execute("select id from sale_history_line where user_id != new_user_id")
            ids_to_show = list(filter(None, map(lambda x: x[0], cr.fetchall())))
            domain += [('id', 'in', ids_to_show)]
        res = super(Sale_History_Line, self).read_group(domain, fields, groupby, offset, limit, orderby, lazy)
        return res
