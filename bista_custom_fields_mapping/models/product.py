# -*- encoding: utf-8 -*-
##############################################################################
#
#    Bista Solutions Pvt. Ltd
#    Copyright (C) 2023 (http://www.bistasolutions.com)
#
#############################################################################
from odoo import fields, models, api,_
from odoo.exceptions import UserError
import json


class ProductTemlate(models.Model):
    _inherit = 'product.template'

    product_vendor_code = fields.Char(string='Vendor Code',compute='get_vendor_code')
    picking_count = fields.Integer(string='Delivered', compute='_compute_received_items')
    default_vendor = fields.Many2one(string='Default Vendor', comodel_name='res.partner',
                                     domain=[('supplier_rank', '>', 0)])
    received_date = fields.Datetime('Product Received Date', copy=False,
                                    help='Last received date of the product from a vendor.')
    not_returnable = fields.Boolean('Not Returnable')
    product_brand_id = fields.Many2one('product.brand', string='Brand', help='Select a brand for this product')

    label_line_ids = fields.One2many('product.label.line', 'product_tmpl_id', 'Product Labels',
                                     help="Set the number of product labels")
    product_brand_ept_id = fields.Many2one(
        'product.brand',
        string='Brand',
        help='Select a brand for this product'
    )
    tab_line_ids = fields.One2many('product.tab.line', 'product_id', 'Product Tabs', help="Set the product tabs")
    document_ids = fields.Many2many('ir.attachment', string="Documents",
                                    domain="[('mimetype', 'not in', ('application/javascript','text/css'))]")
    available_in_pos = fields.Boolean(string='Available in POS',default=True, help='Check if you want this product to appear in the Point of Sale.')

    @api.constrains('tab_line_ids')
    def check_tab_lines(self):
        if len(self.tab_line_ids) > 4:
            raise UserError(_("You can not create more then 4 tabs!!"))

    def _compute_received_items(self):
        # product_ids = self.with_context(active_test=False).product_variant_ids.ids
        for res in self:
            stock_moves = self.env['stock.move'].search(
                [('product_id.product_tmpl_id', '=', res.id), ('state', '=', 'done'),
                 ('picking_id.picking_type_id.code', '=', 'incoming')])
            received_pickings = self.env['stock.picking'].search_count(
                [('state', '=', 'done'), ('move_ids', 'in', stock_moves.ids),
                 ('picking_type_id.code', '=', 'incoming')])
            res.picking_count = received_pickings

    @api.depends('seller_ids', 'seller_ids.product_code')
    def get_vendor_code(self):
        for res in self:
            if len(res.seller_ids) > 0:
                res.product_vendor_code = res.seller_ids[0].product_code
            else:
                res.product_vendor_code = ''


class ProductProduct(models.Model):
    _inherit = 'product.product'

    product_vendor_code = fields.Char(string='Vendor Code',compute='get_vendor_code')
    picking_count = fields.Integer(string='Delivered', compute='_compute_received_items')
    product_brand_id = fields.Many2one('product.brand', string='Brand', help='Select a brand for this product')
    actual_margin = fields.Char('Actual Gross Margin %', compute='calculate_actual_margin')

    var_desc = fields.Char('Variant description', compute='_compute_var_desc', store=True)
    pos_seq = fields.Integer('POS Sequence')

    @api.depends('product_template_attribute_value_ids', 'name')
    def _compute_var_desc(self):
        # FIXME can avoid loop?
        for rec in self:
            idAndName = rec.name_get()[0]
            rec.var_desc = idAndName[1] if idAndName else None

    @api.depends('lst_price')
    def calculate_actual_margin(self):
        for res in self:
            if res.lst_price > 0:
                actual_margin = ((res.lst_price - res.standard_price) / res.lst_price) * 100
                res.actual_margin = str(round(actual_margin, 2)) + ' %'
            else:
                res.actual_margin = ''
    def _compute_received_items(self):
        for res in self:
            stock_moves = self.env['stock.move'].search([('product_id', '=', res.id), ('state', '=', 'done'),
                                                         ('picking_id.picking_type_id.code', '=', 'incoming')])
            received_pickings = self.env['stock.picking'].search_count(
                [('state', '=', 'done'), ('move_ids', 'in', stock_moves.ids),
                 ('picking_type_id.code', '=', 'incoming')])
            res.picking_count = received_pickings

    @api.depends('seller_ids', 'seller_ids.product_code')
    def get_vendor_code(self):
        for res in self:
            if res.seller_ids.filtered(lambda p: p.product_id == res):
                res.product_vendor_code = res.seller_ids.filtered(lambda p: p.product_id == res)[0].product_code
            else:
                res.product_vendor_code = ''

    def action_view_picking_list(self):
        self.ensure_one()
        action = self.env.ref('stock.action_picking_tree_all')
        product_ids = self.with_context(active_test=False).product_variant_ids.ids

        return {
            'name': action.name,
            'help': action.help,
            'type': action.type,
            'view_mode': action.view_mode,
            'target': action.target,
            'context': "{'default_product_id': " + str(product_ids[0]) + " ,'active_product_id': "+ str(product_ids[0]) +"}",
            'res_model': action.res_model,
            'domain': [('state', 'in', ['done']), ('product_id', '=', self.id),('picking_type_id.code','=','incoming')],
        }


class ProductAttribute(models.Model):
    _inherit = 'product.attribute'

    is_quick_filter = fields.Boolean(string='Quick Filter', help="It will show this attribute in quick filter")
    website_ids = fields.Many2many('website', help="You can set the filter in particular website.")
    exclude_website_ids = fields.Many2many('website', 'website_exclude_rel', string="Hide from Product Filter",
                                           help="Exclude the Attribute from Product Filter listing as well as Quick Filter based on Website selection.")
    icon_style = fields.Selection(selection=[('round', "Round"), ('square', "Square"), ], string="Icon Style",
                                  default='round', help="Here, Icon size is 40*40")


class ProductAttributeValue(models.Model):
    _inherit = 'product.attribute.value'

    products_count = fields.Integer(compute="_compute_product_count", string='Products Count', copy=False, default=0)
    short_code = fields.Char(string='Short Code')

    def _compute_product_count(self):
        for value in self:
            product_template_attribute_value = self.env['product.template.attribute.line'].search([('value_ids', 'in', [value.id])])
            products_count = 0
            for res in product_template_attribute_value:
                products_count += res.product_tmpl_id.product_variant_count
            value.products_count = products_count

    def action_view_products_list(self):
        product_template_attribute_value = self.env['product.template.attribute.line'].search([('value_ids','in',[self.id])])

        product_ids = []
        for res in product_template_attribute_value:
            if res.product_tmpl_id.product_variant_ids:
                product_ids.extend(res.product_tmpl_id.product_variant_ids.ids)

        return {
            'name': _('Products'),
            'view_mode': 'tree,form',
            'res_model': 'product.product',
            'type': 'ir.actions.act_window',
            'domain': [('id', 'in', product_ids)],
        }

class ProductSupplierInfo(models.Model):
    _inherit = 'product.supplierinfo'

    name = fields.Char()
    sale_price = fields.Float(string='Retail Price')
    product_id_domain = fields.Char('Product Domain', compute='_domain_product_id')
    price = fields.Float(
        'Cost', default=0.0, digits='Product Price',
        required=True, help="The price to purchase a product")
    mark_up = fields.Float(string='Mark-up')
    product_id = fields.Many2one(
        'product.product', 'Product Variant', check_company=True, domain=[],
        help="If not set, the vendor price will apply to all variants of this product.")

    @api.onchange('price', 'mark_up', 'sale_price')
    def calc_price(self):
        if self.price and self.mark_up:
            self.sale_price = math.trunc(self.price * self.mark_up)
        elif self.sale_price and self.mark_up:
            self.price = round(self.sale_price / self.mark_up)

    @api.depends('product_tmpl_id')
    def _domain_product_id(self):
        for rec in self:
            if self.env.context.get('default_product_tmpl_id'):
                domain = [('product_tmpl_id', '=', self.env.context.get('default_product_tmpl_id'))]
            elif rec.product_tmpl_id and not isinstance(rec.product_tmpl_id.id, models.NewId):
                domain = [('product_tmpl_id', '=', rec.product_tmpl_id.id)]
            elif self.env.context.get('params') and self.env.context.get('params').get(
                    'model') and self.env.context.get(
                    'params').get('model') == 'product.template' and self.env.context['params'].get('id'):
                domain = [('product_tmpl_id', '=', self.env.context['params'].get('id'))]
            else:
                domain = []
            rec.product_id_domain = json.dumps(domain)

class Pricelist(models.Model):
    _inherit = 'product.pricelist'

    available_in_pos = fields.Boolean(string='Avialabe In POS')
    need_manager_approval = fields.Boolean(string='Need Manager Approval')

    offer_msg = fields.Char(string="Offer Message", translate=True,
                            help="To set the message in the product offer timer.", size=35)
    is_display_timer = fields.Boolean(string='Display Timer', help="It shows the product timer on product page.")

class ProductCategory(models.Model):
    _inherit = 'product.category'

    linked_attributes = fields.Many2many(comodel_name='product.attribute',string='Attributes')
    # linked_website_categories = fields.Many2one(comodel_name='product.public.category',string='Website Category')
    linked_website_categories = fields.Many2many(comodel_name='product.public.category',string='Website Category')
    pos_category = fields.Many2one(comodel_name='pos.category',string='Pos Category')
    is_parent_categ_attributes_linked = fields.Boolean(compute='get_parent_categ_attributes',store=True)
    margin = fields.Float('Gross Margin %')
    l_1 = fields.Many2one(comodel_name='product.attribute', string='L1')
    l_2 = fields.Many2one(comodel_name='product.attribute', string='L2')
    l_3 = fields.Many2one(comodel_name='product.attribute', string='L3')
    l_4 = fields.Many2one(comodel_name='product.attribute', string='L4')
    l_5 = fields.Many2one(comodel_name='product.attribute', string='L5')

    r_1 = fields.Many2one(comodel_name='product.attribute', string='R1')
    r_2 = fields.Many2one(comodel_name='product.attribute', string='R2')
    r_3 = fields.Many2one(comodel_name='product.attribute', string='R3')
    r_4 = fields.Many2one(comodel_name='product.attribute', string='R4')
    r_5 = fields.Many2one(comodel_name='product.attribute', string='R5')
    short_code = fields.Char(string='Short Code')
    consignment_valuation_account = fields.Many2one(
        'account.account', 'Stock Input Consigee Account', company_dependent=True,
        domain="[('company_id', '=', allowed_company_ids[0]), ('deprecated', '=', False)]", check_company=True,
        help="""When create a purchase invoice will pull up the consignee account.""", )


    @api.depends('parent_id.linked_attributes')
    def get_parent_categ_attributes(self):
        for rec in self:
            attributes=rec.parent_id.linked_attributes
            for attribute in attributes:
                if not rec.linked_attributes.filtered(lambda a:a ==attribute):
                    rec.linked_attributes = [(4,attribute.id)]
            rec.is_parent_categ_attributes_linked=True