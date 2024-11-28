# -*- coding: utf-8 -*-

from . import models
from . import controllers
from odoo.addons.payment import setup_provider, reset_payment_provider


def post_init_hook(cr):
    setup_provider(cr, 'eway')


def uninstall_hook(cr):
    reset_payment_provider(cr, 'eway')

