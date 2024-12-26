from odoo import fields, models, api
from odoo.exceptions import UserError, ValidationError


class MrpWorkOrder(models.Model):
    _inherit = 'mrp.workorder'

    def action_open_manufacturing_order(self):
        action = self.with_context(no_start_next=True).do_finish()
        try:
            with self.env.cr.savepoint():
                res = self.production_id.button_mark_done()
                if res is not True:
                    if 'context' not in res:
                        res['context'] = {}
                    res['context'] = dict(res['context'], from_workorder=True)
                    return res
        except (UserError, ValidationError) as e:
            # log next activity on MO with error message
            self.production_id.activity_schedule(
                'mail.mail_activity_data_warning',
                note=e.name,
                summary=('The %s could not be closed') % (self.production_id.name),
                user_id=self.env.user.id)
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'mrp.production',
                'views': [[self.env.ref('mrp.mrp_production_form_view').id, 'form']],
                'res_id': self.production_id.id,
                'target': 'main',
            }
        return action
