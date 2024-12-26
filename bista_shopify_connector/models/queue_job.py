from odoo import _, api, exceptions, fields, models
import re


class QueueJob(models.Model):

    _inherit = 'queue.job'

    def open_related_action(self):
        if self.func_string and 'shopify.log.line' in self.func_string:
            pattern = r"shopify\.log\.line\((\d+),?\)"
            match = re.search(pattern, self.func_string)
            if match:
                extracted_number = match.group(1)
                log_id = self.env['shopify.log.line'].browse(int(extracted_number))
                if log_id.related_model_name and log_id.related_model_id:
                    return log_id.view_related_record()

        return super(QueueJob, self).open_related_action()
            
