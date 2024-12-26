from odoo import fields, models, api


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    waring_message = fields.Char("Credit Limit Warning Message", config_parameter='base_setup.default_waring_message',
                                 readonly=False)
    blocking_message = fields.Char('Credit Limit Blocking Message',
                                   config_parameter='base_setup.default_blocking_message', readonly=False)
    bista_payment_term_id = fields.Many2one(
        comodel_name='account.payment.term',
        config_parameter='bista_customer_credit_limit.bista_payment_term_id',

        string="Default Payment Terms"
    )

    @api.model
    def set_values(self):
        config_parameter = self.env["ir.config_parameter"].sudo()
        config_parameter.set_param("bista_payment_term_id", self.bista_payment_term_id.id or False)
        return super().set_values()

    @api.model
    def get_values(self):
        res = super().get_values()
        params = self.env["ir.config_parameter"].sudo()
        config_parameter = int(params.get_param("bista_payment_term_id", False)) or False
        res.update({"bista_payment_term_id": config_parameter})
        return res
