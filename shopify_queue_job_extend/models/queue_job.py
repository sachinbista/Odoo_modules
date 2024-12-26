from odoo import _, api, models, fields


class QueueJob(models.Model):
    _inherit = 'queue.job'

    is_task = fields.Boolean("Is Task")

    @api.model_create_multi
    def create(self, vals_list):
        res = super(QueueJob, self).create(vals_list)
        for job in res:
            if job.job_function_id.is_task:
                job.is_task = True
        return res


class QueueJobFunction(models.Model):
    _inherit = 'queue.job.function'

    is_task = fields.Boolean("Is Task")
