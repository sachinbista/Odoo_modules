# -*- coding: utf-8 -*-

from . import controllers
from . import models
from . import common

from odoo import api, SUPERUSER_ID


def _post_init_pick_hook(cr, registry):
    env = api.Environment(cr, SUPERUSER_ID, {})
    env['stock.warehouse'].action_pick_operation()