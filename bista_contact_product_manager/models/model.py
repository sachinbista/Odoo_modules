from odoo import models, fields, api, _
from odoo.exceptions import UserError


class ResPartner(models.Model):
    _inherit = "res.partner"

    @api.model_create_multi
    def create(self, vals):
        res = super(ResPartner, self).create(vals)
        if not self.env.user.has_group('bista_contact_product_manager.contact_product_edit_restriction'):
            raise UserError(_("You don't have access to Edit and Create."))
        else:
            return res

    @api.model
    def write(self, vals):
        res = super(ResPartner, self).write(vals)
        if not self.env.user.has_group('bista_contact_product_manager.contact_product_edit_restriction'):
            raise UserError(_("You don't have access to Edit and Create."))
        else:
            return res


class ProductTemplate(models.Model):
    _inherit = "product.template"

    hs_code = fields.Char(
        string="HS Code",
        company_dependent=True,
        help="Standardized code for international shipping and goods declaration. At the moment, only used for the FedEx shipping provider.",
    )

    @api.model_create_multi
    def create(self, vals):
        res = super(ProductTemplate, self).create(vals)
        if not self.env.user.has_group('bista_contact_product_manager.contact_product_edit_restriction')and not self.env.user.has_group(
                'bista_product_manager.group_product_edit_access'):
            raise UserError(_("You don't have access to Edit and Create"))
        else:
            return res

    @api.model
    def write(self, vals):
        res = super(ProductTemplate, self).write(vals)
        if not self.env.user.has_group(
                'bista_contact_product_manager.contact_product_edit_restriction') and not self.env.user.has_group(
                'bista_product_manager.group_product_edit_access'):
            raise UserError(_("You don't have access to Edit and Create."))
        return res


class ProductProduct(models.Model):
    _inherit = "product.product"

    @api.model_create_multi
    def create(self, vals):
        res = super(ProductProduct, self).create(vals)
        if not self.env.user.has_group('bista_contact_product_manager.contact_product_edit_restriction')and not self.env.user.has_group(
                'bista_product_manager.group_product_edit_access'):
            raise UserError(_("You don't have access to Edit and Create"))
        else:
            return res

    @api.model
    def write(self, vals):
        res = super(ProductProduct, self).write(vals)
        if not self.env.user.has_group('bista_contact_product_manager.contact_product_edit_restriction')and not self.env.user.has_group(
                'bista_product_manager.group_product_edit_access'):
            raise UserError(_("You don't have access to Edit and Create."))
        else:
            return res


    @api.depends('name', 'barcode')
    def _compute_display_name(self):
        """
            This method display name updated
        """
        for record in self:
            if record.barcode:
                record.display_name = '[' + record.barcode + '] ' + record.name
            else:
                record.display_name = f"{record.name}"

class ProductCategory(models.Model):
    _inherit = "product.category"

    @api.model_create_multi
    def create(self, vals):
        res = super(ProductCategory, self).create(vals)
        if not self.env.user.has_group('bista_contact_product_manager.contact_product_edit_restriction'):
            raise UserError(_("You don't have access to Edit and Create"))
        else:
            return res

    @api.model
    def write(self, vals):
        res = super(ProductCategory, self).write(vals)
        if not self.env.user.has_group('bista_contact_product_manager.contact_product_edit_restriction'):
            raise UserError(_("You don't have access to Edit and Create."))
        else:
            return res
