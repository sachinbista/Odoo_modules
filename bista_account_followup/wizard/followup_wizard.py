from odoo import models, fields, api
import base64


class CustomerStatementWizard(models.TransientModel):
    _name = 'customer.statement.wizard'
    _description = 'Customer Statement Wizard'

    file_data = fields.Binary('File')
    file_name = fields.Char('File Name')

    def generate_customer_statement(self):
        active_id = self.env.context.get('active_id')
        partner = self.env['res.partner'].browse(active_id)
        if partner:
            file_data, file_name = partner.customer_statement_excel_report()
            self.write({
                # 'file_data': base64.b64encode(file_data),
                'file_data': file_data.decode('utf-8'),
                'file_name': file_name,
            })

            # Return an action to download the file
            return {
                'type': 'ir.actions.act_url',
                'url': f'/web/content/{self._name}/{self.id}/file_data/{file_name}',
                'target': 'new',
            }
