from . import models

from odoo import api, SUPERUSER_ID
def _pre_init_sale_order_management(cr, registry):
    env = api.Environment(cr, SUPERUSER_ID, {})
    sale_order = env['sale.order'].search([('state', 'in', ['sale', 'sent', 'hold'])])
    sale_line_report = env['sale.line.report'].search([])
    for rec in sale_order:
        order_exists = any(sale_line.order_id.id == rec.id for sale_line in sale_line_report)
        if not order_exists:
            rec.create_sale_line_report()

