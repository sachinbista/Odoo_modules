from odoo import models, fields, api, _
from odoo.exceptions import UserError


class OutstandingPaymentLine(models.Model):
    _name = 'outstanding.payment.line'
    _description = "Outstanding Payment Lines"
    _rec_name = 'reference'
    _order = 'payment_date'

    # this will used for one2many in payment
    payment_id = fields.Many2one('account.payment', string="Payment", ondelete="cascade")
    move_id = fields.Many2one(
        'account.move',
        string="Move",
        help="This is invoice/bill moves")
    reference = fields.Char(string="Reference", required=True)
    # this is payment id of outstanding payment
    move_payment_id = fields.Many2one('account.payment', string="Payment")
    currency_id = fields.Many2one('res.currency', string="Currency")
    move_line_id = fields.Many2one('account.move.line', string="Move Line")
    payment_date = fields.Date(string='Payment Date')
    amount_residual = fields.Float(string='Residual',
                                   digits='Product Price')
    amount_to_utilize = fields.Float(string="Utilize",
                                     digits='Product Price')
    source_id = fields.Reference(
        selection=[('account.move', 'Move'),
                   ('account.payment', 'Payment')],
        store=True,
        string="Source Document", compute='_get_source_document')
    
    common_allocation_id = fields.Many2one('common.allocation', string="Common Allocation", ondelete="cascade")
    is_current_payment = fields.Boolean(string="Is Current Payment", help="This is used to identify current payment", copy=False)

    def unlink(self):
        for rec in self:
            if rec.common_allocation_id:
                rec.common_allocation_id.unlink()
        return super(OutstandingPaymentLine, self).unlink()

    @api.depends('move_payment_id', 'move_id')
    def _get_source_document(self):
        for rec in self:
            if rec.move_payment_id:
                rec.source_id = rec.move_payment_id
            elif rec.move_id:
                rec.source_id = rec.move_id
            else:
                rec.source_id = False

    def update_residual_amount(self):
        for rec in self:
            if rec.move_line_id.move_id.state == 'posted' and rec.move_line_id.amount_residual:
                rec.amount_residual = rec.move_line_id.amount_residual
            else:
                rec.payment_id.outstanding_payment_ids = [(3, rec.id)]

    @api.onchange('amount_to_utilize')
    def onchange_amount_to_utilize(self):
        if self.amount_residual < 0:
            sign = -1
        else:
            sign = 1
        self.amount_to_utilize = abs(self.amount_to_utilize) * sign

        if round(abs(self.amount_to_utilize), 2) > round(
                abs(self.amount_residual), 2):
            raise UserError(
                _("Amount to utilize should not be greater than residual amount."))

    def write(self, vals):
        res = super(OutstandingPaymentLine, self).write(vals)
        if self._context.get('from_common'):
            return res
        if 'amount_to_utilize' in vals:
            self.common_allocation_id.with_context(from_payment=True).allocation = vals['amount_to_utilize']
        return res
