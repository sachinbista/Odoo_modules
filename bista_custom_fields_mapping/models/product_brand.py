from odoo import api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools.translate import _

class ProductBrand(models.Model):

    _inherit = 'product.brand'
    _description = 'Product Brand'

    # _inherit = ['website.published.multi.mixin']

    def _get_website_url(self):
        for res in self:
            res.website_url = "/page/product_brands_family?brand=%s" %(res.id)

    # name = fields.Char('Brand Name', required=True)
    # description = fields.Text('Description', translate=True)
    # partner_id = fields.Many2one('res.partner',string='Partner',help='Select a partner for this brand if any.',ondelete='restrict')
    # logo = fields.Binary('Logo File')
    product_ids = fields.One2many('product.template','product_brand_id',string='Brand Products',)
    products_count = fields.Integer(string='Number of products',compute='_get_products_count',)
    product_count = fields.Integer(string='Number of products',compute='_get_products_count',)
    # families = fields.One2many(comodel_name='product.brand.family',inverse_name='brand_id',string='Families')
    # website_url = fields.Char(string='URL', compute='_get_website_url')
    # active = fields.Boolean(string='Active',default=True)
    # website_published = fields.Boolean(default=True)

    # is_brand_page = fields.Boolean(string='Is Brand Page',help="It will set the separate landing page for this brand")
    # brand_page = fields.Many2one("website.page", string="Brand Page",help="Select the brand page which you want to set for this brand.")
    # is_featured_brand = fields.Boolean(string='Is Featured Brand')
    # allow_in_brand_slider = fields.Boolean(string='Allow In Brand Slider',help="You can set this brand in Brand carousel snippets.")

    def website_publish_button(self):
        self.ensure_one()
        return self.write({'website_published': not self.website_published})

    @api.depends('product_ids')
    def _get_products_count(self):
        for each in self:
            each.products_count = len(each.product_ids)
            each.product_count = len(each.product_ids)

    @api.constrains('allow_in_brand_slider')
    def validate_brand_carousel(self):
        if not self.logo and self.allow_in_brand_slider:
            raise ValidationError(_("Please set the brand image before set this in carousel"))

    # @api.depends('product_ids')
    # def _compute_products_count(self):
    #     for brand in self:
    #         brand.products_count = len(brand.product_ids)

    def set_brand_wizard(self):
        action = {
            'type': 'ir.actions.act_window',
            'res_model': 'product.brand.config',
            'name': "Product Brand Configuration",
            'view_mode': 'form',
            'target': 'new',
            'context': dict(default_brand_id=self.id),
        }
        return action


# class ProductBrandFamily(models.Model):
#     _name = 'product.brand.family'
#     _description = 'Product Family'
#
#     name = fields.Char(string='Family Name',required=True)
#     brand_id = fields.Many2one(comodel_name='product.brand',string='Brand',required=True)
#     logo = fields.Binary(string='Family Image')
