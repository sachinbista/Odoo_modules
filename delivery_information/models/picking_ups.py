from odoo import api, models, fields, _, tools
import requests
import csv
import json
from dotenv import load_dotenv
from odoo.exceptions import UserError, ValidationError
import base64
from datetime import datetime
from dateutil import parser

class StockPicking(models.Model):
    _inherit = 'stock.picking'

    ups_picking_tracking_line = fields.One2many('ups.track.line', 'picking_id')
    ups_add_track_no = fields.Boolean('Add Ups track Number', default=False)

    @api.constrains('ups_picking_tracking_line')
    def _check_exist_track_line(self):
        for rec in self:
            track_no_in_lines = rec.mapped('ups_picking_tracking_line.track_no')
            for track in track_no_in_lines:
                lines_count = len(rec.ups_picking_tracking_line.filtered(lambda line: line.track_no == track))
                if lines_count > 1:
                    raise ValidationError(_('You cannot add same track No in line items'))

    def generate_token(self):

        carrier_id = self.env['delivery.carrier'].search([('name', '=', 'UPS US')])
        client_key = carrier_id.ups_username
        client_secret = carrier_id.ups_passwd
        account = carrier_id.ups_shipper_number
        url = 'https://wwwcie.ups.com/security/v1/oauth/token'

        payload = {
            "grant_type": "client_credentials"
        }

        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "x-merchant-id": account
        }

        response = requests.post(url, data=payload, headers=headers, auth=(client_key,client_secret))

        access = response.json()
        token = access['access_token']
        return token

    def convert_date(self,dt):
        date_obj = datetime.strptime(dt, "%Y%m%d")
        formatted_date = date_obj.strftime("%m/%d/%Y")
        return formatted_date

    def track_ups_ship_rout(self):
        token = self.generate_token()
        carrier_id = self.env['delivery.carrier'].search([('name', '=', 'UPS US')])
        ship_ids = self.env['stock.picking'].search([('shipped', '=', False), ('ups_add_track_no', '=', True)])

        for ship_id in ship_ids:
            for line in ship_id.ups_picking_tracking_line:
                if line.delivered == False:

                    url = "https://onlinetools.ups.com/api/track/v1/details/" + line.track_no

                    headers = {
                        "transId": "string",
                        "transactionSrc": "string",
                        "Authorization": f"Bearer {token}"
                    }

                    response = requests.get(url, headers=headers, )
                    track_records = response.json()
                    print('\n\n------------',track_records)
                    if track_records['trackResponse']['shipment'][0]:
                        if 'warnings' in track_records['trackResponse']['shipment'][0]:
                            print('\n\n',track_records['trackResponse']['shipment'][0]['warnings'][0]['message'])
                        else:

                            data = track_records['trackResponse']['shipment'][0]['package'][0]
                            carrier_id = self.env['delivery.carrier'].search([('name', 'ilike', 'UPS US')])
                            if data['currentStatus']['description'] == 'Delivered':
                                current_status = 'Delivered'
                                line.write({
                                    'status': current_status,
                                    'carrier_id': carrier_id.id,
                                    'delivered': True
                                })

                                val = {
                                    'location': data['packageAddress'][0]['address']['city']
                                                + ', ' + data['packageAddress'][0]['address']['stateProvince'] +
                                                ', ' + data['packageAddress'][0]['address']['country'],
                                    'from_date': self.convert_date(data['activity'][0]['gmtDate']) + ' ' +
                                                 data['activity'][0]['gmtTime'],
                                    'status': data['currentStatus']['description'],
                                    'track_no': data['trackingNumber'],
                                    'start_from': self.convert_date(data['activity'][-1]['gmtDate']) + ' ' +
                                                  data['activity'][-1]['gmtTime'],
                                    'picking_id': ship_id.id,
                                    'dest_location': data['packageAddress'][1]['address']['city'] +
                                                     ', ' + data['packageAddress'][1]['address']['stateProvince'] +
                                                     ', ' + data['packageAddress'][1]['address']['country'],
                                    'received_by': data['deliveryInformation']['receivedBy'],

                                    'label_loc' : data['activity'][-1]['location']['address']['country'],
                                    'label_date': self.convert_date(data['activity'][-1]['date'])+ ' ' +
                                                  data['activity'][-1]['gmtTime'],

                                    'on_the_way3':data['activity'][2]['location']['address']['city']
                                                    + ', ' + data['activity'][2]['location']['address']['stateProvince'] +
                                                    ', ' + data['activity'][2]['location']['address']['country'],
                                    'on_the_way_date':self.convert_date(data['activity'][2]['date'])+ ' ' +
                                                    data['activity'][2]['gmtTime'],

                                    'out_for_delivery':data['activity'][1]['location']['address']['city']
                                                       + ', ' + data['activity'][1]['location']['address']['stateProvince'] +
                                                       ', ' + data['activity'][1]['location']['address']['country'],
                                    'out_for_delivery_date':self.convert_date(data['activity'][1]['date'])+ ' ' +
                                                    data['activity'][1]['gmtTime'],

                                    'delivery':data['activity'][0]['location']['address']['city']
                                               + ', ' + data['activity'][0]['location']['address']['stateProvince'] +
                                               ', ' + data['activity'][0]['location']['address']['country'],
                                    'delivered_date':self.convert_date(data['activity'][0]['date'])+ ' ' +
                                                    data['activity'][0]['gmtTime'],
                                }

                                res = self.env['tracking.details'].search(
                                    [('picking_id', '=', ship_id.id), ('status', '=', val['status']),
                                     ('track_no', '=', val['track_no'])])
                                if res:
                                    pass
                                else:
                                    date_obj = datetime.strptime(val['from_date'], "%m/%d/%Y %H:%M:%S")
                                    formatted_date = date_obj.strftime("%Y-%m-%d %H:%M:%S")

                                    label_date_obj = datetime.strptime(val['label_date'], "%m/%d/%Y %H:%M:%S")
                                    label_formatted_date = label_date_obj.strftime("%Y-%m-%d %H:%M:%S")

                                    on_the_way_date_obj = datetime.strptime(val['on_the_way_date'], "%m/%d/%Y %H:%M:%S")
                                    on_the_way_formatted_date = on_the_way_date_obj.strftime("%Y-%m-%d %H:%M:%S")

                                    out_for_delivery_date_obj = datetime.strptime(val['out_for_delivery_date'], "%m/%d/%Y %H:%M:%S")
                                    out_of_delivery_formatted_date = out_for_delivery_date_obj.strftime("%Y-%m-%d %H:%M:%S")

                                    delivered_date_date_obj = datetime.strptime(val['delivered_date'], "%m/%d/%Y %H:%M:%S")
                                    delivery_date_formatted_date = delivered_date_date_obj.strftime("%Y-%m-%d %H:%M:%S")

                                    self.env['tracking.details'].create({
                                        'track_no': val['track_no'],
                                        'status': val['status'],
                                        'location': val['location'],
                                        'from_date': formatted_date,
                                        'picking_id': val['picking_id'],
                                        'dest_location': val['dest_location'],
                                        'receivedByName': val['received_by'],
                                        'start_from':val['label_loc'],
                                        'label_date':label_formatted_date,
                                        'on_the_way3':val['on_the_way3'],
                                        'on_the_way_date':on_the_way_formatted_date,
                                        'out_for_delivery':val['out_for_delivery'],
                                        'out_for_delivery_date':out_of_delivery_formatted_date,
                                        'delivered':val['delivery'],
                                        'delivered_date':delivery_date_formatted_date

                                    })

                            else:
                                current_status = data['currentStatus']['description']
                                line.write({
                                    'status': current_status,
                                    'carrier_id': carrier_id.id,
                                    'delivered': False
                                })


                                val = {
                                    'location':data['packageAddress'][0]['address']['city']
                                               + ', ' + data['packageAddress'][0]['address']['stateProvince']+
                                               ', '+data['packageAddress'][0]['address']['country'],
                                    'from_date': self.convert_date(data['activity'][0]['gmtDate'])+' '+data['activity'][0]['gmtTime'],
                                    'status':data['currentStatus']['description'],
                                    'track_no':data['trackingNumber'],
                                    'start_from':self.convert_date(data['activity'][0]['gmtDate'])+' '+data['activity'][0]['gmtTime'],
                                    'picking_id':ship_id.id,
                                    'dest_location':data['packageAddress'][1]['address']['city']+
                                                    ', '+data['packageAddress'][1]['address']['stateProvince']+
                                                    ', '+data['packageAddress'][1]['address']['country'],

                                    }
                                res = self.env['tracking.details'].search(
                                    [('picking_id', '=', ship_id.id), ('status', '=', val['status']),
                                     ('track_no', '=', val['track_no'])])
                                if res:
                                    pass
                                else:
                                    date_obj = datetime.strptime(val['from_date'], "%m/%d/%Y %H:%M:%S")

                                    # Format to the desired output format
                                    formatted_date = date_obj.strftime("%Y-%m-%d %H:%M:%S")

                                    self.env['tracking.details'].create({
                                        'track_no': val['track_no'],
                                        'status': val['status'],
                                        'location': val['location'],
                                        'from_date': formatted_date,
                                        'picking_id': val['picking_id'],
                                        'dest_location': val['dest_location'],


                                    })



class FedextrackLine(models.Model):
    _name = 'ups.track.line'

    picking_id = fields.Many2one('stock.picking')
    track_no = fields.Char('Tracking Number')
    carrier_id = fields.Many2one('delivery.carrier',string='Carrier')
    current_status = fields.Char('Current Status')
    file = fields.Binary('Proof Docs')
    attachment_id = fields.Many2one('ir.attachment', string="Attachment")
    delivered = fields.Boolean('Delivered')
    status = fields.Char('Current Status')
    account_no = fields.Char('Account Number')
