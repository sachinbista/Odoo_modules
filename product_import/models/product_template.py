# -*- coding: utf-8 -*-
#############################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2024-TODAY Cybrosys Technologies(<https://www.cybrosys.com>)
#    Author: Aysha Shalin (odoo@cybrosys.com)
#
#    You can modify it under the terms of the GNU AFFERO
#    GENERAL PUBLIC LICENSE (AGPL v3), Version 3.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU AFFERO GENERAL PUBLIC LICENSE (AGPL v3) for more details.
#
#    You should have received a copy of the GNU AFFERO GENERAL PUBLIC LICENSE
#    (AGPL v3) along with this program.
#    If not, see <http://www.gnu.org/licenses/>.
#
#############################################################################
import requests
import base64
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class ProductTemplate(models.Model):
    """ Inheriting 'product.template' for adding image url """
    _inherit = 'product.template'

    image_url = fields.Char(string='Image URL', help="Url of Image")
    image_added = fields.Binary("Image (1920x1920)",
                                compute='_compute_image_added', store=True,
                                help="Uploaded Image")


    @api.depends('image_url')
    def _compute_image_added(self):
        """ Function to load an image from URL or local file path """
        image = False
        for rec in self:
            if rec.image_url:
                if rec.image_url.startswith(('http://', 'https://')):
                    # Load image from URL
                    try:
                        image = base64.b64encode(
                            requests.get(rec.image_url).content)
                    except Exception as e:
                        # Handle URL loading errors
                        raise UserError(
                            _(f"Error loading image from URL: {str(e)}"))
                else:
                    # Load image from local file path
                    try:
                        with open(rec.image_url, 'rb') as image_file:
                            image = base64.b64encode(image_file.read())
                    except Exception as e:
                        # Handle local file loading errors
                        raise UserError(
                            _(f"Error loading image from local path: {str(e)}"))
            image_added = image
            if image_added:
                rec.image_1920 = image_added


class ProductVariantImage(models.Model):
    """ Inheriting 'product.product' for adding image url """
    _inherit = 'product.product'

    image_url = fields.Char(string='Image URL', help="Url of Image")
    image_added = fields.Binary("Image",
                                compute='_compute_image_added', store=True,
                                help="Uploaded Image")
    image_line = fields.One2many('product.images','product_id')

    @api.constrains('image_line')
    def set_main_image(self):
        for res in self.image_line:

            count = len(self.env['product.images'].search([('id','in',self.image_line.ids),('set_main','=',True)]))
            if count > 1:
                raise ValidationError(_('You cannot set multiple images'))
            if res.set_main == True:
                self.update({
                    'image_url':res.url
                })

    #
    # @api.constrains('image_line')
    # def set_as_main_image(self):
    #
    #
    #     for rec in self.image_line:
    #         if rec.set_main == True:
    #             set_in_lines = rec.mapped('image_line.set_main')
    #             for set in set_in_lines:
    #                 lines_count = len(rec.image_line.filtered(lambda line: line.set_main == True))
    #                 if lines_count > 1:
    #                     raise ValidationError(_('You cannot set multiple images'))

    @api.onchange('image_url')
    def _onchange_image_url(self):
        if self.image_url:
            try:
                response = requests.get(self.image_url)
                if response.status_code == 200:
                    self.image = base64.b64encode(response.content)
            except Exception as e:
                # Handle exceptions (e.g., invalid URL, network issues)
                pass

    @api.depends('image_url')
    def _compute_image_added(self):
        """ Function to load an image from URL or local file path """
        image = False
        for rec in self:
            if rec.image_url:
                if rec.image_url.startswith(('http://', 'https://')):
                    # Load image from URL
                    try:
                        image = base64.b64encode(
                            requests.get(rec.image_url).content)
                    except Exception as e:
                        # Handle URL loading errors
                        raise UserError(
                            _(f"Error loading image from URL: {str(e)}"))
                else:
                    # Load image from local file path
                    try:
                        with open(rec.image_url, 'rb') as image_file:
                            image = base64.b64encode(image_file.read())
                    except Exception as e:
                        # Handle local file loading errors
                        raise UserError(
                            _(f"Error loading image from local path: {str(e)}"))
            image_added = image
            if image_added:
                rec.image_1920 = image_added



class ProductVariantImageIst(models.Model):
    """ Class to store iamges """
    _name = 'product.images'

    product_id = fields.Many2one('product.product')
    url = fields.Char('Image Url')
    name = fields.Char('Image Name')
    image_added = fields.Binary("Image (1920x1920)",
                                compute='_compute_image_added', store=True,
                                help="Uploaded Image")
    image_1920 = fields.Image(compute='_compute_image_1920', readonly=False, store=True)
    set_main = fields.Boolean('Set As Main',default=False)

    @api.onchange('url')
    def _onchange_image_url(self):
        if self.url:
            try:
                response = requests.get(self.url)
                if response.status_code == 200:
                    self.image_1920 = base64.b64encode(response.content)
            except Exception as e:
                # Handle exceptions (e.g., invalid URL, network issues)
                pass
        # if self.image_added:
        #     self.image_1920 = self.image_added





