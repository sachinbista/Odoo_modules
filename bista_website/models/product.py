# -*- encoding: utf-8 -*-
##############################################################################
#
#    Bista Solutions Pvt. Ltd
#    Copyright (C) 2016 (http://www.bistasolutions.com)
#
##############################################################################

from odoo import fields, models, api


class ProductImage(models.Model):
    _inherit = 'product.image'
    # TODO: remove is_certificate field
    is_certificate = fields.Boolean('Is Certificate')


class ProductAttribute(models.Model):
    _inherit = 'product.attribute'

    is_certificate = fields.Boolean('Is Certificate')


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    has_digital_certificate = fields.Boolean('Has Digital Certificate', compute='_compute_has_digital_certificate', store=True)

    @api.depends('dr_ptav_ids', 'dr_ptav_ids.attribute_id.is_certificate')
    def _compute_has_digital_certificate(self):
        for product in self:
            product.has_digital_certificate = any(product.dr_ptav_ids.filtered(lambda x: x.attribute_id.is_certificate))

    def _get_images(self):
        """Return a list of records implementing `image.mixin` to
        display on the carousel on the website for this template.

        This returns a list and not a recordset because the records might be
        from different models (template and image).

        It contains in this order: the main image of the template and the
        Template Extra Images.
        """
        self.ensure_one()
        return [self] + list(self.product_template_image_ids.filtered(lambda img: not img.is_certificate))
