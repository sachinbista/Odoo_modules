from odoo import models, api, fields, _
from odoo.exceptions import UserError
import datetime
import time
from datetime import date, datetime, timedelta

SPLIT_METHOD = [
    ('equal', 'Equal'),
    ('by_quantity', 'By Quantity'),
    ('by_current_cost_price', 'By Current Cost'),
    ('by_weight', 'By Weight'),
    ('by_volume', 'By Volume'),
]


def calculate_difference_compact(list1, list2):
    dict1 = dict(list1)
    dict2 = dict(list2)
    return [[name, dict2.get(name, 0) - dict1.get(name, 0)] for name in dict1]


class StockLandedCost(models.Model):
    _inherit = 'stock.landed.cost'

    flag = fields.Boolean('Flag')
    landed_cost_id = fields.Many2one('stock.landed.cost')
    standard_line = fields.One2many('standard.landed.cost','cost_id')
    purchase_id = fields.Many2one('purchase.order', 'Purchase Order')
    fiscal_position_id = fields.Many2one('account.fiscal.position', string='Fiscal Position',
                                         copy=False)

    # def action_set_draft(self):
    #     self.write({'state': 'draft'})

    def default_get(self, fields):
        res = super().default_get(fields)
        fiscal_position_id = self.env['account.fiscal.position'].search([
            ('is_intercompany_po', '=', True),
            ('company_id','=',res.get('company_id'))], limit=1)
        if fiscal_position_id:
            res['fiscal_position_id'] = fiscal_position_id.id
        return res

    def _prepare_account_move_vals(self):
        move_vals = super()._prepare_account_move_vals()
        move_vals['internal_order_ref'] = self.internal_order_ref
        return move_vals


    @api.onchange('internal_order_ref')
    def onchange_internal_order_ref(self):
        picking_obj = self.env['stock.picking'].sudo()
        for rec in self:
            if rec.internal_order_ref:
                picking_id = picking_obj.search([('internal_order_ref', '=', rec.internal_order_ref)],limit=1)
                if picking_id:
                    self.write({'picking_ids': [(4, picking_id.id)]})

    def button_validate(self):
        if self.fiscal_position_id:
            self = self.with_context(fiscal_position_id=self.fiscal_position_id.id)
        res = super().button_validate()
        account_payment_register_obj = self.env['account.payment.register'].sudo()
        purchase_orders = self.picking_ids.mapped('purchase_id')

        if self.account_move_id:
            self.account_move_id.write({
                'internal_order_ref': self.internal_order_ref,
            })

        for purchase_order in purchase_orders:
            if purchase_order.parent_company_id and purchase_order.parent_purchase_order_id:
                po_id = purchase_order.parent_purchase_order_id.sudo()
                # vendor_bill_id = po_id.invoice_ids.filtered(lambda x: x.state == 'posted')
                picking_ids = po_id.picking_ids.filtered(lambda x: x.state == 'done')
                not_done_picking_ids = po_id.picking_ids.filtered(lambda x: x.state != 'done' and x.state != 'cancel')
                standard_line = [
                    (0, 0, {
                        'name': line.name,
                        'product_id': line.product_id.id,
                        'price_unit': line.price_unit,
                        'split_method': line.split_method,
                        'account_id': line.account_id.id,
                        'currency_id': line.currency_id.id,
                        'cost_id': self.id,
                    })
                    for line in self.mapped('standard_line')
                ]
                if picking_ids:
                    bill_obj = self.create_landed_bill(po_id)
                    company_id = po_id.company_id
                    bill_obj.action_post()
                    bill_obj.button_create_custom_landed_costs(picking_ids,standard_line)
                    payment_journal_id=self.env['account.journal'].sudo().search([('is_vendor_journal','=',True),
                                                                           ('company_id','=',company_id.id)])
                    payment_wizard = account_payment_register_obj.with_company(company_id.id).with_context(
                        active_ids=bill_obj.line_ids.ids,
                        active_model='account.move.line', default_journal_id=payment_journal_id,
                        company_id=company_id.id).create({})
                    payment = payment_wizard.sudo().action_create_payments()
                    res_id = payment.get('res_id')
                    if res_id:
                        payment_obj = self.env['account.payment'].sudo().search([('id', '=', res_id)])
                        payment_obj.internal_order_ref = po_id.internal_order_ref

                elif not_done_picking_ids:
                    company_id = po_id.company_id
                    landed_costs = self.env['stock.landed.cost'].with_company(company_id.id).create({
                        'purchase_id': po_id.id,
                        'internal_order_ref': self.internal_order_ref,
                        'cost_lines': [(0, 0, {
                            'product_id': l.product_id.id,
                            'name': l.product_id.name,
                            'account_id': l.product_id.product_tmpl_id.with_company(company_id.id).get_product_accounts()['stock_input'].id,
                            'price_unit': l.price_unit,
                            'split_method': l.product_id.split_method_landed_cost or 'equal',
                        }) for l in self.cost_lines],
                    })
                    # bill_obj.button_create_custom_landed_costs(not_done_picking_ids,standard_line)

    def create_landed_bill(self,po_id):
        company_id = po_id.company_id
        move_lines = []
        for cost_line in self.cost_lines:
            move_line = {
                'product_id': cost_line.product_id.id,
                'name': cost_line.product_id.name,
                'price_unit': cost_line.price_unit,
                'quantity': 1.0,
                'product_uom_id': cost_line.product_id.uom_id.id,
                'is_landed_costs_line': True,
            }
            move_lines.append((0, 0, move_line))

        bill_vals = {
            'move_type': 'in_invoice',
            'partner_id': self.company_id.partner_id.id,
            'invoice_date': fields.Date.context_today(self),
            'invoice_line_ids': move_lines,
            'company_id': company_id.id,
            'internal_order_ref': po_id.internal_order_ref,
            'ref': self.name,
        }
        landed_cost_bill = self.env['account.move'].with_company(company_id.id).create(bill_vals)
        return landed_cost_bill


    @api.onchange('picking_ids')
    def _onchange_picking_ids(self):
        if not self.picking_ids:
            self.standard_line = False
            return

        landed_costs = self.env['stock.landed.cost'].search([('picking_ids', 'in', self.picking_ids.ids)])
        landed_costs -= self
        cost_lines = [
            (0, 0, {
                'name': line.name,
                'product_id': line.product_id.id,
                'price_unit': line.price_unit,
                'split_method': line.split_method,
                'account_id': line.account_id.id,
                'currency_id': line.currency_id.id,
                'cost_id': self.id,
            })
            for line in landed_costs.mapped('cost_lines')
        ]
        self.standard_line = cost_lines

        for line in self.cost_lines:
            standard_line = self.standard_line.filtered(lambda x: x.product_id == line.product_id)
            if standard_line:
                line.price_unit -= standard_line.price_unit


class AccountMove(models.Model):
    _inherit = 'account.move'

    def button_create_custom_landed_costs(self, picking_ids=None,standard_line=None):
        """Create a `stock.landed.cost` record associated to the account move of `self`, each
        `stock.landed.costs` lines mirroring the current `account.move.line` of self.
        """
        if picking_ids:
            self.ensure_one()
            landed_costs_lines = self.line_ids.filtered(lambda line: line.is_landed_costs_line)

            landed_costs = self.env['stock.landed.cost'].with_company(self.company_id).create({
                'vendor_bill_id': self.id,
                'internal_order_ref': self.internal_order_ref,
                'picking_ids':picking_ids.ids,
                'purchase_id': picking_ids.purchase_id.id if picking_ids.purchase_id else False,
                'cost_lines': [(0, 0, {
                    'product_id': l.product_id.id,
                    'name': l.product_id.name,
                    'account_id': l.product_id.product_tmpl_id.get_product_accounts()['stock_input'].id,
                    'price_unit': l.currency_id._convert(l.price_subtotal, l.company_currency_id, l.company_id,
                                                         l.move_id.date),
                    'split_method': l.product_id.split_method_landed_cost or 'equal',
                }) for l in landed_costs_lines],
            })
            landed_costs.standard_line = standard_line
            if landed_costs and picking_ids.state == 'done':
                landed_costs.button_validate()
            action = self.env["ir.actions.actions"]._for_xml_id("stock_landed_costs.action_stock_landed_cost")
            return dict(action, view_mode='form', res_id=landed_costs.id, views=[(False, 'form')])

    def button_create_landed_costs(self):
        res = super().button_create_landed_costs()
        landed_costs = self.landed_costs_ids.filtered(lambda x: x.state == 'draft')
        landed_costs.internal_order_ref = self.internal_order_ref
        landed_costs.onchange_internal_order_ref()
        landed_costs._onchange_picking_ids()
        return res



                # code for landed cost creation
                # cost_lines = []
                # landed_cost_obj = self.env['stock.landed.cost']
                # for line in self.cost_lines:
                #     accounts_data = line.product_id.product_tmpl_id.with_company(company_id).get_product_accounts()
                #     account_id = accounts_data['stock_input']
                #     cost_lines.append((0, 0, {
                #         'name': line.name,
                #         'product_id': line.product_id.id,
                #         'price_unit': line.price_unit,
                #         'split_method': line.split_method,
                #         'account_id': account_id.id,
                #     }))
                #
                # if self.flag == False:
                #     landed_cost = landed_cost_obj.with_company(company_id).create({
                #         'picking_ids': [(4, pid) for pid in picking_ids.ids],
                #         'cost_lines': cost_lines,
                #         'vendor_bill_id': vendor_bill_id.id,
                #         'landed_cost_id': self.id,
                #     })
                #     landed_cost.button_validate()
        # return res







class StandardLandedCost(models.Model):
    _name = 'standard.landed.cost'

    name = fields.Char('Description')
    cost_id = fields.Many2one('stock.landed.cost', 'Landed Cost',required=True, ondelete='cascade')
    product_id = fields.Many2one('product.product', 'Product', required=True)
    price_unit = fields.Monetary('Cost', required=True)
    split_method = fields.Selection( SPLIT_METHOD,string='Split Method',required=True,)
    account_id = fields.Many2one('account.account', 'Account', domain=[('deprecated', '=', False)])
    currency_id = fields.Many2one('res.currency', related='cost_id.currency_id')


    # def create_vendor_bill(self):
    #
    #     self.ensure_one()
    #
    #     purchase_orders = self.picking_ids.mapped('purchase_id')
    #
    #     for purchase_order in purchase_orders:
    #
    #         po_id = purchase_order.parent_purchase_order_id.sudo()
    #         picking_ids = po_id.picking_ids
    #         company_id = po_id.company_id
    #         # print('----------------------------po',po_id)
    #         # picking_ids = po_id.picking_ids
    #         # company_id = purchase_order.parent_company_id
    #         print('--------------------', company_id)
    #
    #     return res



            #
            # account_obj = self.env['account.move'].with_company(company_id).create(bill_vals)
            #     # self.vendor_bill_id = bill.id
            # return account_obj

        # return True

        # def button_validate(self):
    #     res = super().button_validate()
    #     purchase_orders  = self.picking_ids.mapped('purchase_id')
    #     landed_cost_obj = self.env['stock.landed.cost']
    #     for purchase_order in purchase_orders:
    #         if purchase_order.parent_company_id and purchase_order.parent_purchase_order_id:
    #             po_id = purchase_order.parent_purchase_order_id.sudo()
    #             picking_ids = po_id.picking_ids
    #             company_id = po_id.company_id
    #             vendor_bill_id = po_id.invoice_ids.filtered(lambda x: x.state == 'posted')
    #             cost_lines = []
    #             for line in self.cost_lines:
    #                 accounts_data = line.product_id.product_tmpl_id.with_company(company_id).get_product_accounts()
    #                 account_id = accounts_data['stock_input']
    #                 cost_lines.append((0, 0, {
    #                     'name': line.name,
    #                     'product_id': line.product_id.id,
    #                     'price_unit': line.price_unit,
    #                     'split_method': line.split_method,
    #                     'account_id': account_id.id,
    #
    #                 }))
    #
    #             if self.flag==False:
    #                 landed_cost = landed_cost_obj.with_company(company_id).create({
    #                     'picking_ids': [(4, pid) for pid in picking_ids.ids],
    #                     'cost_lines': cost_lines,
    #                     'vendor_bill_id': vendor_bill_id.id,
    #                     'landed_cost_id':self.id,
    #                 })
    #                 landed_cost.button_validate()
    #                 self.flag = True
    #                 self.landed_cost_id=landed_cost.id
    #
    #             elif self.flag==True:
    #                 # self.landed_cost_id.cost_lines.sudo().unlink()
    #                 self.landed_cost_id.sudo().update({
    #                     'cost_lines': cost_lines,
    #                 })





        # return res
