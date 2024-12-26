from odoo import models, api,fields,_
from odoo import models, fields, api, exceptions


class Partner(models.Model):
    _inherit = 'res.partner'

    @api.onchange('name')
    def _check_name_length(self):
        for record in self:
            if record.name and len(record.name) > 50:
                raise exceptions.ValidationError('The name must not exceed 50 characters.')

    debtor_timw_to_pay = fields.Char(string='Average debtor days/time to pay')
    insured_amount = fields.Char(string='Insured Amount')
    certificate_expiry_date = fields.Date('Resale certificate expiry date')
    group_id = fields.Many2one('partner.group',string='Groups')
    group_ids = fields.Many2many('partner.group',string='Groups')
    invoice_type = fields.Selection([('email', 'Email'),
                                     ('portal', 'Portal'),
                                     ('edi', 'EDI')],string='Invoice type')
    channel_ids = fields.Many2many('partner.channel','channel_id',string="Channels")
    payment_methods = fields.Many2many('account.payment.method.line','payment_methods',String="Payment Methods")
    invoice_payment_method = fields.Many2many('invoice.payment.method',)
    invoice_send = fields.Boolean('Can Send Invoice')
    discount = fields.Float(string="Discount (%)")
    is_require_shipping = fields.Boolean(string="Required Shipping")
    report_company = fields.Char(string="Report Company")


class Groups(models.Model):
    _name = 'partner.group'

    name = fields.Char(string="Group Name")


class Channel(models.Model):
    _name = 'partner.channel'

    name = fields.Char(string="Channel Name")
    channel_id = fields.Many2one('partner.channel')
    
class invoice_payment_method(models.Model):
    _name = 'invoice.payment.method'

    name = fields.Char('Payment Method')
    desc = fields.Html('Descriptions')
    payment_method_id = fields.Many2one('payment.method',string='Payment Provider',
                                          domain="[('active', '=', True)]")
    
