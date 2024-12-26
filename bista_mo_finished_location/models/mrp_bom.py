# -*- coding: utf-8 -*-
# Bista Solutions Pvt. Ltd
# Copyright (C) 2023 (https://www.bistasolutions.com)

from odoo import models, fields


class MrpBom(models.Model):
    _inherit = 'mrp.bom'

    location_dest_id = fields.Many2one(
        'stock.location', 'Finished Products Location',
        domain="[('usage','=','internal'), '|', ('company_id', '=', False), ('company_id', '=', company_id)]",
        check_company=True,tracking=True,
        help="Location where the system will stock the finished products.")
