from odoo import models, fields, api, _
from odoo.exceptions import UserError
from odoo.osv import expression
import re


class ResPartner(models.Model):
    _inherit = "res.partner"

    @api.constrains('write_date')
    def _check_user_permission(self):
        if self._context and not self._context.get('model') == "res.users":
            for rec in self:
                if not self.env.user.has_group('bista_contact_product_manager.contact_product_edit_restriction'):
                    raise UserError(_("You don't have access to create records."))


    # @api.model_create_multi
    # def create(self, vals_list):
    #     if not self.env.user.has_group('bista_contact_product_manager.contact_product_edit_restriction'):
    #         raise UserError(_("You don't have access to create records."))
    #     return super(ResPartner, self).create(vals_list)
    #
    # def write(self, vals):
    #     if not self.env.user.has_group('bista_contact_product_manager.contact_product_edit_restriction'):
    #         raise UserError(_("You don't have access to edit records."))
    #     return super(ResPartner, self).write(vals)

    # @api.model_create_multi
    # def create(self, vals):
    #     res = super(ResPartner, self).create(vals)
    #     if not self.env.user.has_group('bista_contact_product_manager.contact_product_edit_restriction'):
    #         raise UserError(_("You don't have access to Edit and Create."))
    #     else:
    #         return res
    #
    # @api.model
    # def write(self, vals):
    #     res = super(ResPartner, self).write(vals)
    #     if not self.env.user.has_group('bista_contact_product_manager.contact_product_edit_restriction'):
    #         raise UserError(_("You don't have access to Edit and Create."))
    #     else:
    #         return res


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
    def _name_search(self, name, domain=None, operator='ilike', limit=None, order=None):
        domain = domain or []
        if name:
            positive_operators = ['=', 'ilike', '=ilike', 'like', '=like']
            product_ids = []
            if operator in positive_operators:
                product_ids = list(self._search([('barcode', '=', name)] + domain, limit=limit, order=order))
                if not product_ids:
                    product_ids = list(self._search([('barcode', '=', name)] + domain, limit=limit, order=order))
            if not product_ids and operator not in expression.NEGATIVE_TERM_OPERATORS:
                # Do not merge the 2 next lines into one single search, SQL search performance would be abysmal
                # on a database with thousands of matching products, due to the huge merge+unique needed for the
                # OR operator (and given the fact that the 'name' lookup results come from the ir.translation table
                # Performing a quick memory merge of ids in Python will give much better performance
                product_ids = list(self._search(domain + [('barcode', operator, name)], limit=limit, order=order))
                if not limit or len(product_ids) < limit:
                    # we may underrun the limit because of dupes in the results, that's fine
                    limit2 = (limit - len(product_ids)) if limit else False
                    product2_ids = self._search(domain + [('name', operator, name), ('id', 'not in', product_ids)],
                                                limit=limit2, order=order)
                    product_ids.extend(product2_ids)
            elif not product_ids and operator in expression.NEGATIVE_TERM_OPERATORS:
                domain2 = expression.OR([
                    ['&', ('barcode', operator, name), ('name', operator, name)],
                    ['&', ('barcode', '=', False), ('name', operator, name)],
                ])
                domain2 = expression.AND([domain, domain2])
                product_ids = list(self._search(domain2, limit=limit, order=order))
            if not product_ids and operator in positive_operators:
                ptrn = re.compile(r'(\[(.*?)\])')
                res = ptrn.search(name)
                if res:
                    product_ids = list(
                        self._search([('barcode', '=', res.group(2))] + domain, limit=limit, order=order))
            # still no results, partner in context: search on supplier info as last hope to find something
            if not product_ids and self._context.get('partner_id'):
                suppliers_ids = self.env['product.supplierinfo']._search([
                    ('partner_id', '=', self._context.get('partner_id')),
                    '|',
                    ('product_code', operator, name),
                    ('product_name', operator, name)])
                if suppliers_ids:
                    product_ids = self._search([('product_tmpl_id.seller_ids', 'in', suppliers_ids)], limit=limit,
                                               order=order)
        else:
            product_ids = self._search(domain, limit=limit, order=order)
        return product_ids

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
                # record.display_name = '[' + record.barcode + '] ' + record.name
                record.display_name =  record.name + ' - ' + record.barcode
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
