##############################################################################
#
# Bista Solutions Pvt. Ltd
# Copyright (C) 2022 (http://www.bistasolutions.com)
#
##############################################################################


from odoo import fields, models,api, _
from odoo.exceptions import AccessError, ValidationError


class Partner(models.Model):
    _name = "shopify.channel"

    name = fields.Char('Channel')
    online_store = fields.Boolean('Is Online Store?')
    amazon_store = fields.Boolean('Is Amazon?')
    shopify_config_id = fields.Many2one('shopify.config', "Shopify Configuration",
                                        ondelete='cascade')

    @api.constrains('online_store')
    def _check_online_store(self):
        for rec in self:
            if rec.online_store:
                search_rec_count = self.search_count(
                    [('online_store', '=', True)])
                if search_rec_count > 1:
                    raise ValidationError(
                        _('Only 1 channel is configure as a Online Channel'))
        return True

    @api.constrains('amazon_store')
    def _check_amazon_store(self):
        for rec in self:
            if rec.amazon_store:
                search_rec_count = self.search_count(
                    [('amazon_store', '=', True)])
                if search_rec_count > 1:
                    raise ValidationError(
                        _('Only 1 channel is configure as a Amazon Channel'))
        return True


