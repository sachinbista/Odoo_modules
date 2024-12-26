# -*- coding: utf-8 -*-

import json

import werkzeug.urls
import werkzeug.utils
from datetime import timedelta, date
from odoo.http import request
from odoo.tools import image_process
from werkzeug.exceptions import NotFound
from odoo.tools.safe_eval import safe_eval

import odoo
import logging

from odoo import fields, models, http
from odoo.addons.auth_oauth.controllers.main import OAuthLogin
from odoo.addons.website_sale_wishlist.controllers.main import WebsiteSale
from odoo.addons.website_sale_wishlist.controllers.main import WebsiteSaleWishlist
_logger = logging.getLogger(__name__)

class Website(models.Model):
    _inherit = "website"

    facebook_sharing = fields.Boolean(string='Facebook')
    twitter_sharing = fields.Boolean(string='Twitter')
    linkedin_sharing = fields.Boolean(string='Linkedin')
    mail_sharing = fields.Boolean(string='Mail')
    is_load_more = fields.Boolean(string='Load More', help="Load more will be enabled", readonly=False)
    load_more_image = fields.Binary('Load More Image', help="Display this image while load more applies.",
                                    readonly=False)
    button_or_scroll = fields.Selection([
        ('automatic', 'Automatic- on page scroll'),
        ('button', 'Button- on click button')
    ], string="Loading type for products",
        required=True, default='automatic', readonly=False)
    prev_button_label = fields.Char(string='Label for the Prev Button', readonly=False,
                                    default="Load prev", translate=True)
    next_button_label = fields.Char(string='Label for the Next Button', readonly=False,
                                    default="Load next", translate=True)
    is_lazy_load = fields.Boolean(string='Lazyload', help="Lazy load will be enabled", readonly=False)
    lazy_load_image = fields.Binary('Lazyload Image', help="Display this image while lazy load applies.",
                                    readonly=False)
    banner_video_url = fields.Many2one('ir.attachment', "Video URL", help='URL of a video for banner.', readonly=False)
    number_of_product_line = fields.Selection([
        ('1', '1'),
        ('2', '2'),
        ('3', '3')
    ], string="Number of lines for product name", default='1', readonly=False, help="Number of lines to show in product name for shop.")
    is_auto_play = fields.Boolean(string='Slider Auto Play', default=True, readonly=False)

    is_pwa = fields.Boolean(string='PWA', readonly=False, help="Pwa will be enabled.")
    pwa_name = fields.Char(string='Name', readonly=False)
    pwa_short_name = fields.Char(string='Short Name', readonly=False)
    pwa_theme_color = fields.Char(string='Theme Color', readonly=False)
    pwa_bg_color = fields.Char(string='Background Color', readonly=False)
    pwa_start_url = fields.Char(string='Start URL', readonly=False)
    app_image_512 = fields.Binary(string='Application Image(512x512)', readonly=False, store=True)
    is_price_range_filter = fields.Boolean(string='Price Range Filter', help="Enable the price range filter")
    price_filter_on = fields.Selection([
        ('list_price', 'On Product Sale Price'),
        ('website_price', 'On Product Discount Price')
    ], string="Price Range Filter For Products",
        default='list_price', readonly=False)
