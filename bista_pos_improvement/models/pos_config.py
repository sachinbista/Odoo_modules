# -*- coding: utf-8 -*-
##############################################################################
#
# Bista Solutions Pvt. Ltd
# Copyright (C) 2023 (http://www.bistasolutions.com)
#
##############################################################################

from odoo import models, fields, _

class PosConfig(models.Model):
    _inherit = 'pos.config'

    def get_limited_partners_loading(self):
        self.env.cr.execute("""
            WITH pm AS
            (
                     SELECT   partner_id,
                              Count(partner_id) order_count
                     FROM     pos_order
                     GROUP BY partner_id)
            SELECT    id
            FROM      res_partner AS partner
            LEFT JOIN pm
            ON        (
                                partner.id = pm.partner_id)
            WHERE (
                partner.company_id=%s
            )
            ORDER BY  COALESCE(pm.order_count, 0) DESC,
                      NAME limit %s;
        """, [self.company_id.id, str(self.limited_partners_amount)])
        result = self.env.cr.fetchall()
        return result

