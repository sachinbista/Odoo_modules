from odoo import api, fields, models
import  requests
from odoo.exceptions import UserError

class AcceptBluecConfiguration(models.Model):
    _name='accept.blue.config'

    api_url=fields.Char('Url')
    name=fields.Char('Name')
    source_key=fields.Char('Source Key')
    pin_code=fields.Char('Pin')
    prod_environment = fields.Boolean("Environment", default=True)




    def toggle_prod_environment(self):
        """This method is to switch environment from test to production and vice-versa"""
        for record in self:
            record.prod_environment = not record.prod_environment
            if record.prod_environment:
                record.api_url='https://api.accept.blue/api/v2/'
            else:
                record.api_url = 'https://api.develop.accept.blue/api/v2/'



