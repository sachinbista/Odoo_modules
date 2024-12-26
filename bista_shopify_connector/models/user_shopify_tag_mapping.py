from odoo import api, _, fields, models
from odoo.exceptions import ValidationError


class UserShopifyTagMapping(models.Model):
    _name = 'user.shopify.tag'
    _description = "user.shopify.tag"

    shopify_tag_ids = fields.Many2one('shopify.tags', string='Shopify Tags')
    user_id = fields.Many2one('res.users', string='User')

    @api.constrains('shopify_tag_ids', 'user_id')
    def check_temp(self):
        tags = self.env['user.shopify.tag'].search([
            ('id', '!=', self.id), '|',
            ('shopify_tag_ids', '=', self.shopify_tag_ids.id),
            ('user_id', '=', self.user_id.id)])
        if tags:
            raise ValidationError(
                "Fields Shopify Tags and User must be unique for each record.")
