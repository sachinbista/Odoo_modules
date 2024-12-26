from odoo import models, fields, api


class WebsiteMenu(models.Model):
    _inherit = 'website.menu'

    public_category_id = fields.Many2one('product.public.category',
                                         string='Related Category',
                                         help="Set a category to Shop By Style menu item")
    product_attribute_ids = fields.Many2many('product.attribute',
                                             string='Related Attributes',
                                             help="Set attributes to Shop By Style menu item")
    main_category_id = fields.Many2one('product.public.category',
                                       string='Related Category',
                                       help="Set a category which will be interlinked with Menu Attribute")
    menu_attribute_ids = fields.One2many('website.menu.attribute',
                                         'menu_id',
                                         string='Menu Attributes',
                                         delete='cascade',
                                         help="Set attributes to Shop By Style menu item")
    menu_category_ids = fields.One2many('website.menu.category',
                                        'menu_id',
                                        string='Menu Categories',
                                        delete='cascade',
                                        help="Set categories to Shop By Style menu item")


class WebsiteMenuCategory(models.Model):
    _name = 'website.menu.category'
    _description = 'Website Menu Category Configuration'
    _order = 'sequence'

    def _get_default_menu_name(self):
        return f"Shop By {self.related_category_id.name}"

    sequence = fields.Integer(string='Sequence', default=10)
    related_category_id = fields.Many2one('product.public.category',
                                          string='Related Category',
                                          required=True)
    menu_name = fields.Char(
        string='Menu Name', required=True, default=_get_default_menu_name)
    menu_id = fields.Many2one('website.menu', string='Menu', required=True)
    view_all_name = fields.Char(string='View All Name', default='',
                                help='Set a name for View All button. Prefix "View All" will be added automatically.')

    @api.onchange('related_category_id')
    def _onchange_related_category_id(self):
        if self.related_category_id:
            self.menu_name = self._get_default_menu_name()


class WebsiteMenuAttribute(models.Model):
    _name = 'website.menu.attribute'
    _description = 'Website Menu Attribute Configuration'
    _order = 'sequence'

    def _get_default_menu_name(self):
        return f"Shop By {self.related_attribute_id.name}"

    sequence = fields.Integer(string='Sequence', default=10)
    related_attribute_id = fields.Many2one('product.attribute',
                                           string='Related Attribute',
                                           required=True)
    menu_name = fields.Char(
        string='Menu Name', required=True, default=_get_default_menu_name)
    menu_id = fields.Many2one('website.menu', string='Menu', required=True)
    view_all_name = fields.Char(string='View All Name', default='',
                                help='Set a name for View All button. Prefix "View All" will be added automatically.')

    @api.onchange('related_attribute_id')
    def _onchange_related_attribute_id(self):
        if self.related_attribute_id:
            self.menu_name = self._get_default_menu_name()
