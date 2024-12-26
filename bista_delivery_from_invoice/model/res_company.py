from odoo import models, fields, api, _


class ResCompany(models.Model):
    _inherit = "res.company"

    is_delivery_invoice = fields.Boolean(string="Is Delivery From Invoice",company_dependent=False,
                                         help="Is Create Delivery Order From Customer Invoice")
    warehouse_id = fields.Many2one("stock.warehouse",company_dependent=False, string="Warehouse")
    out_picking_type = fields.Many2one("stock.picking.type",company_dependent=False, string="Operation Type")
    return_pickng_type = fields.Many2one("stock.picking.type",company_dependent=False, string="Return Operation Type")
