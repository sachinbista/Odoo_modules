import logging

from odoo import models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class ProductProduct(models.Model):
    _inherit = "product.product"

    def action_open_label_layout(self):
        return self.print_label()

    def print_label(self):
        active_model = self.env.context.get('active_model')
        active_ids = self.env.context.get("active_ids") if active_model == 'product.product' else self.ids
        products = self.env['product.product'].browse(active_ids)
        if not products:
            raise UserError("There is not record to print. If you believe "
                            "this is due to a technical error. Please Contact System Administrator")
        product_tmp_ids = products.mapped("product_tmpl_id").ids
        action = self.env['ir.actions.act_window']._for_xml_id('bista_zpl_labels.print_wizard_action')
        action['context'] = {'default_model': 'product.template', 'default_product_ids': [(6, 0, product_tmp_ids)]}
        return action
