from odoo import models, fields, api, _
from odoo.exceptions import UserError


class CommonAllocation(models.Model):
    _name = 'common.allocation'
    _description = "Common Allocation"
    _rec_name = 'reference'
    _order = 'is_outstanding_line, date'

    select = fields.Boolean(string="Select")
    linked_payment_id = fields.Many2one('account.payment', string="Payment")
    reference = fields.Char(string="Reference")
    invoice_line_id = fields.Many2one('payment.invoice.line', string="Invoice Line")
    invoice_id = fields.Many2one('account.move', string="Invoice")
    date = fields.Date(string="Date")
    total_amount = fields.Float(string="Total Amount", digits='Product Price')
    amount_residual = fields.Float(string="Residual Amount", digits='Product Price')
    allocation = fields.Float(string="Allocation", digits='Product Price')
    currency_id = fields.Many2one('res.currency', string="Currency")
    amount_allowed_discount = fields.Float(string="Allowed Discount", digits='Product Price')
    discount_amount = fields.Float(string="Applied Discount", digits='Product Price')
    sale_tax = fields.Float(string="Sale Tax", digits='Product Price')
    payment_difference = fields.Float(compute='_get_payment_difference', string="Payment Difference",
                                      digits='Product Price', store=True)
    select_all = fields.Boolean(string="Select All")
    move_line_ids = fields.Many2many('account.move.line', 'rel_common_payment_allocation_move_line_ids',
                                     'allocation_line_id', 'move_line_id',
                                     string="Move Lines", copy=False)
    is_payment_line = fields.Boolean(string="Is Payment Line", help="This is used to current identify payment line",
                                     copy=False)
    check_all_posted = fields.Boolean(related='linked_payment_id.check_all_posted', string="Check All Posted",
                                      copy=False, store=True, depends=['linked_payment_id.check_all_posted'])
    outstanding_line_id = fields.Many2one('outstanding.payment.line', string="Outstanding Payment")
    move_id = fields.Many2one(
        'account.move',
        string="Move",
        help="This is invoice/bill moves")
    reference = fields.Char(string="Reference")
    move_payment_id = fields.Many2one('account.payment', string="Payment")
    move_line_id = fields.Many2one('account.move.line', string="Move Line")
    payment_date = fields.Date(string='Payment Date')
    is_outstanding_line = fields.Boolean(string="Is Outstanding Line", help="This is used to identify outstanding line",
                                         copy=False)
    state = fields.Selection([('draft', 'Draft'), ('posted', 'Posted')],
                             string='Status', default='draft')

    writeoff_account_id = fields.Many2one('account.account', string='Write-Off Account')
    discount_account_id = fields.Many2one('account.account', string='Discount Discount')

    def write(self, vals):
        res = super(CommonAllocation, self).write(vals)

        if self._context.get('from_payment'):
            return res

        # update allocation in original line
        if 'allocation' in vals and self.invoice_line_id:
            self.invoice_line_id.with_context(from_common=True).allocation = vals['allocation']
            self.invoice_line_id.with_context(from_common=True).onchange_make_select_all()

        if 'discount_amount' in vals and self.invoice_line_id:
            self.invoice_line_id.with_context(from_common=True).discount_amount = vals['discount_amount']
            self.invoice_line_id.with_context(from_common=True).onchange_make_select_all()

        if 'sale_tax' in vals and self.invoice_line_id:
            self.invoice_line_id.with_context(from_common=True).sale_tax = vals['sale_tax']
            self.invoice_line_id.with_context(from_common=True).onchange_make_select_all()

        if 'select_all' in vals and self.invoice_line_id:
            self.invoice_line_id.with_context(from_common=True).select_all = vals['select_all']

        if 'select' in vals and self.invoice_line_id:
            self.invoice_line_id.with_context(from_common=True).select = vals['select']

        if 'state' in vals and self.invoice_line_id:
            self.invoice_line_id.with_context(from_common=True).state = vals['state']

        if 'allocation' in vals and self.outstanding_line_id:
            self.outstanding_line_id.with_context(from_common=True).amount_to_utilize = vals['allocation']
            self.outstanding_line_id.with_context(from_common=True).onchange_amount_to_utilize()

        return res

    @api.depends('allocation', 'amount_residual', 'discount_amount')
    def _get_payment_difference(self):
        for rec in self:
            rec.payment_difference = rec.amount_residual - \
                                     rec.allocation - rec.discount_amount - rec.sale_tax

    @api.onchange('discount_amount', 'allocation', 'sale_tax')
    def onchange_make_select_all(self):
        self.onchange_discount_amount_sign()
        self.onchange_sale_tax_amount_sign()
        self.onchange_allocation_sign()
        total = self.discount_amount + self.allocation + self.sale_tax
        total = round(total, 2)
        if total == self.amount_residual:
            self.select_all = True
        else:
            self.select_all = False
        allocation = abs(self.discount_amount) + \
                     abs(self.allocation) + abs(self.sale_tax)
        allocation = round(allocation, 2)
        if allocation == 0.0:
            self.select = False
        else:
            self.select = True
        if abs(allocation) > abs(self.amount_residual):
            raise UserError(_('You can not allocate more than open amount.'))

    @api.onchange('discount_amount')
    def onchange_discount_amount_sign(self):
        # change allocation amount if discount amount is greater than open amount
        total_allocation = abs(self.discount_amount) + abs(self.allocation) + abs(self.sale_tax)
        if total_allocation > abs(self.amount_residual):
            self.allocation = abs(self.amount_residual) - abs(self.discount_amount) - abs(self.sale_tax)
            self.onchange_allocation_sign()

        if self.amount_residual < 0:
            self.discount_amount = abs(self.discount_amount) * -1
        else:
            self.discount_amount = abs(self.discount_amount)

    @api.onchange('sale_tax')
    def onchange_sale_tax_amount_sign(self):
        if self.amount_residual < 0:
            self.sale_tax = abs(self.sale_tax) * -1
        else:
            self.sale_tax = abs(self.sale_tax)

    @api.onchange('allocation')
    def onchange_allocation_sign(self):
        if self.amount_residual < 0:
            self.allocation = abs(self.allocation) * -1
        else:
            self.allocation = abs(self.allocation)

    def action_allocate_amount(self):
        self[0].linked_payment_id.select_all_invoice()


    @api.onchange('select')
    def onchange_select(self):
        if self.is_outstanding_line and self.select:
            self.allocation = self.amount_residual