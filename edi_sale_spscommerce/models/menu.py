from odoo import models, api, tools, _, registry
from odoo.http import request
class Menu(models.Model):

    _inherit = 'ir.ui.menu'

    @api.model
    @tools.ormcache('frozenset(self.env.user.groups_id.ids)', 'debug')
    def _visible_menu_ids(self, debug=False):
        menus = super(Menu, self)._visible_menu_ids(debug)
        configs = self.env['edi.config'].search([])
        if not configs or not self.env.user.company_id in configs.mapped('company_ids'):
            menu_item_id = self.env.ref('edi_sale_spscommerce.sale_order_edi').id
            menus.discard(menu_item_id)

        return menus