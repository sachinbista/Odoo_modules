from odoo import tools
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class SaleLineReport(models.Model):
    _name = "truck.schedular"
    _description = "Truck Schedular"

    # schedular = fields.Selection([
    #     ('customer', 'Customer'), ('location', 'Location'), ('carrier', 'Carrier')],
    #                              string="Schedular ")
    customers_id = fields.Many2one('res.partner', string='Customers')
    location_id = fields.Many2one('stock.location',string='Locations')
    carrier_id = fields.Many2one('delivery.carrier',string='Carriers')
    cutoff_time = fields.Float(string="Cut Off Time", required=True, index=True,
        help="Start and End time of working.\n"
             "A specific value of 24:00 is interpreted as 23:59:59.999999.")
    cutoff_time_limit = fields.Float(string="Cut Off Time Limit")
    priority = fields.Integer(string="Priority")
    holiday = fields.Date(string="Holiday")

    @api.onchange('cutoff_time', 'cutoff_time_limit')
    def _onchange_cutoff(self):
        # avoid negative or after midnight
        self.cutoff_time = min(self.cutoff_time, 23.99)
        self.cutoff_time = max(self.cutoff_time, 0.0)
        self.cutoff_time_limit = min(self.cutoff_time_limit, 24)
        self.cutoff_time_limit = max(self.cutoff_time_limit, 0.0)
