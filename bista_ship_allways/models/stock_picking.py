# -*- encoding: utf-8 -*-
##############################################################################
#
#    Bista Solutions Pvt. Ltd
#    Copyright (C) 2023 (http://www.bistasolutions.com)
#
##############################################################################


from odoo import api, fields, models, _
import json
import logging
import requests
from odoo.exceptions import UserError
from datetime import datetime

_logger = logging.getLogger(__name__)


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    def _data_cron_for_fetching_etd_eta(self):
        """Cron job to fetch ETD and ETA for stock pickings."""
        self.env.cr.execute("""SELECT sp.id
                            FROM stock_picking sp
                            LEFT JOIN purchase_order po ON sp.origin = po.name
                            WHERE sp.container_id IS NOT NULL
                            AND sp.state NOT IN ('cancel', 'done')
                            AND sp.picking_type_code = 'incoming'
                            AND sp.origin IS NOT NULL;""")
        fetchall_records = [record[0] for record in self.env.cr.fetchall()]
        picking_ids = self.env['stock.picking'].browse(fetchall_records)
        for picking_id in picking_ids:
            picking_id._onchange_container_id()
            if picking_id.date_etd and picking_id.date_eta and picking_id.container_id == picking_id.batch_id.name and picking_id.batch_id and picking_id.batch_id.state not in ('cancel', 'done'):
                picking_id.batch_id.update({'date_etd':picking_id.date_etd, 'date_eta':picking_id.date_eta})

    
    @api.onchange('container_id')
    def _onchange_container_id(self):
        if not self.container_id:
            self.update({'date_eta': "", 'date_etd': ""})
        else:
            try:
                data = self._make_api_request(self.container_id)
                if data:
                    self.update({
                        'date_eta': fields.Date.from_string(data.get('eta')).isoformat() if data.get('eta') else False,
                        'date_etd': fields.Date.from_string(data.get('etd')).isoformat() if data.get('etd') else False
                    })
                    if self.date_eta:
                        self.move_ids.update({
                            'date': self.date_eta
                            })
                    else:
                        self.move_ids.update({
                            'date':fields.Datetime.now  
                            })

            except requests.exceptions.RequestException as e:
                print(f"Error making API request: {e}")

    def _make_api_request(self, container_id):
        url_param = self.env['ir.config_parameter'].sudo().get_param('bista_ship_allways.url')
        token = self.env['ir.config_parameter'].sudo().get_param('bista_ship_allways.token')

        api_url = f'{url_param}/container/{container_id}'

        try:
            response = requests.get(api_url, headers={'Authorization': f'Bearer {token}'})
            response.raise_for_status()
            return response.json()

        except requests.exceptions.RequestException as e:
            print(f"Error making API request: {e}")
            return {}

