# -*- coding: utf-8 -*-
##############################################################################
#
#    Bista Solutions
#    Copyright (C) 2021 (http://www.bistasolutions.com)
#
##############################################################################
import re

from odoo import api, fields, models, _


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'


    good_shipped_acc_id = fields.Many2one(comodel_name="account.account",
                                          string="Goods Shipped Credit Account")
    bs_po_good_shipped_id = fields.Many2one(comodel_name="account.account",
                                          string="Goods Shipped Debit Account")

    @api.model
    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        params = self.env['ir.config_parameter'].sudo()
        good_shipped_acc_id = params.get_param('good_shipped_acc_id', default=False)
        bs_po_good_shipped_id = params.get_param('bs_po_good_shipped_id', default=False)
        bs_po_good_shipped_id_str = str(bs_po_good_shipped_id)
        match = re.search(r'\((\d+),\)', bs_po_good_shipped_id_str)
        bs_po_good_shipped_id_value = int(match.group(1)) if match else None
        res.update(
            good_shipped_acc_id=int(good_shipped_acc_id),
            bs_po_good_shipped_id=bs_po_good_shipped_id_value,
        )
        return res


    @api.model
    def set_values(self):
        super(ResConfigSettings, self).set_values()
        self.env['ir.config_parameter'].sudo().set_param("good_shipped_acc_id", self.good_shipped_acc_id.id),
        self.env['ir.config_parameter'].sudo().set_param("bs_po_good_shipped_id", self.bs_po_good_shipped_id)
