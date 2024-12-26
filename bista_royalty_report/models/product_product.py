# -*- encoding: utf-8 -*-
##############################################################################
#
#    Bista Solutions Pvt. Ltd
#    Copyright (C) 2023 (http://www.bistasolutions.com)
#
##############################################################################

from odoo.exceptions import ValidationError

from odoo import models, fields, api, _


class ProductProduct(models.Model):
    _inherit = 'product.product'

    product_royalty_list = fields.One2many('product.royalty.list', 'product_id')

    @api.onchange('product_royalty_list')
    def onchange_method(self):
        partner_list = []
        dropship_partner_list = []
        for royalty_line in self.product_royalty_list:
            if royalty_line.partner_id:
                if royalty_line.is_dropship:
                    if royalty_line.partner_id.id in dropship_partner_list:
                        raise ValidationError(
                            _('%s already exists for dropship royalty.' % royalty_line.partner_id.display_name))
                    else:
                        dropship_partner_list.append(royalty_line.partner_id.id)

                if not royalty_line.is_dropship:
                    if royalty_line.partner_id.id in partner_list:
                        raise ValidationError(
                            _('%s already exists for royalty.' % royalty_line.partner_id.display_name))
                    else:
                        partner_list.append(royalty_line.partner_id.id)
