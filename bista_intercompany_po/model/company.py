from docutils.nodes import warning

from odoo import models, api,fields,_, modules
from odoo.exceptions import UserError

@api.model
def _lang_get(self):
    return self.env['res.lang'].get_installed()


class PurchaseOrder(models.Model):
    _inherit = 'res.company'

    first_company_id = fields.Many2one('res.company', company_dependent=False, string='first Company Name')
    secound_company_id = fields.Many2one('res.company',  company_dependent=False, string='Second Company Names')
    is_inter_company = fields.Boolean('Inter Company' ,company_dependent=False)
    lang = fields.Selection(_lang_get, string='Language',
                            help="All the emails and documents sent to this contact will be translated in this language.")


class ResUsers(models.Model):
    _inherit = 'res.users'

    # @api.model
    # def systray_get_activities(self):
    #     """ Update the systray icon of res.partner activities to use the
    #     contact application one instead of base icon. """
    #     activities = super().systray_get_activities()
    #     context = self._context
    #     company_id = self.env['res.company'].sudo().browse(context.get('allowed_company_ids'))
    #     if company_id:
    #         user = self.env.ref('base.user_root')
    #         self.env.user.with_user(user).lang = company_id[0].lang
    #     return activities
