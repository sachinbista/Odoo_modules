from odoo import fields, models, api


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    amazon_commission = fields.Float(string="Amazon Charges (%)", config_parameter='commission.amazon_commission', )

    @api.model
    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        params = self.env['ir.config_parameter'].sudo()
        res.update(amazon_commission=params.get_param('commission.amazon_commission'))
        return res

    def set_values(self):
        super().set_values()
        IrConfigParameter = self.env['ir.config_parameter'].sudo()
        if IrConfigParameter.get_param("commission.amazon_commission"):
            IrConfigParameter.set_param("commission.amazon_commission", self.amazon_commission)
