from odoo import models, fields, api
from odoo.tools.translate import _


class AccountFollowupReport(models.AbstractModel):
    _inherit = 'account.followup.report'

    @api.model
    def _print_followup_letter(self, partner, options=None):
        """Generate the followup letter for the given partner.
        The letter is saved as ir.attachment and linked in the chatter.

        Returns a client action downloading this letter and closing the wizard.
        """

        attachment = options.get("pdf_attachment",False)
        if attachment:
            partner.message_post(body=_('Follow-up letter generated'), attachment_ids=[attachment])
            return {
                'type': 'ir.actions.client',
                'tag': 'close_followup_wizard',
                'params': {
                    'url': '/web/content/%s?download=1' % attachment,
                }
            }
        else:
            return super()._print_followup_letter(partner, options)
