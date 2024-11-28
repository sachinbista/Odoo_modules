from odoo import models, fields, api, _
from odoo.exceptions import UserError


class IrUiMenu(models.Model):
    _inherit = 'ir.ui.menu'

    @api.model
    def get_user_roots(self):
        user = self.env.user
        specific_group = self.env.ref('bista_product_manager.group_product_edit_access')
        admin_user = self.env.ref('base.group_system')
        product_menu = self.env.ref('bista_product_manager.product_menu_root')
        if specific_group in user.groups_id and admin_user not in user.groups_id:
            # Return only the Product menu
            return self.search([('id','=',product_menu.id)])
        # Return the default menu for other users
        return super(IrUiMenu, self).get_user_roots()


class ProductTemplate(models.Model):
    _inherit = "product.template"

    # @api.model_create_multi
    # def create(self, vals):
    #     res = super(ProductTemplate, self).create(vals)
    #     if not self.env.user.has_group('bista_product_manager.product_create_edit_restriction'):
    #         raise UserError(_("You don't have access to Edit and Create"))
    #     else:
    #         return res

    # @api.model
    # def write(self, vals):
    #     res = super(ProductTemplate, self).write(vals)
    #     if not self.env.user.has_group('bista_product_manager.group_product_edit_access'):
    #         raise UserError(_("You don't have access to Edit and Create."))
    #     else:
    #         return res


class ProductProduct(models.Model):
    _inherit = "product.product"

    # @api.model_create_multi
    # def create(self, vals):
    #     res = super(ProductProduct, self).create(vals)
    #     if not self.env.user.has_group('bista_product_manager.product_create_edit_restriction'):
    #         raise UserError(_("You don't have access to Edit and Create"))
    #     else:
    #         return res

    # @api.model
    # def write(self, vals):
    #     res = super(ProductProduct, self).write(vals)
    #     if not self.env.user.has_group('bista_product_manager.group_product_edit_access'):
    #         raise UserError(_("You don't have access to Edit and Create."))
    #     else:
    #         return res

