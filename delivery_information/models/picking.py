from email.policy import default

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

    fedex_tracking_no = fields.Char('Fedex Tracking Number')
    shipped = fields.Boolean('Shipped',default=False)
    picking_tracking_line = fields.One2many('fedex.track.line','picking_id')
    add_track_no = fields.Boolean('Add Fedex track Number',default=False)
    ups_add_track_no = fields.Boolean('Add Ups track Number',default=False)

    def getBearerAuthorization(self):
        # Load client_secret
        load_dotenv()

        headers = {
            'Content-Type': "application/x-www-form-urlencoded"
        }

        carrier_id = self.env['delivery.carrier'].search([('name', '=', 'Fedex US')])
        client_id = carrier_id.fedex_developer_key
        client_secret = carrier_id.fedex_developer_password
        client_url = carrier_id.tracking_client_url
        url = client_url + "/oauth/token"

        AuthHeader = {
            'Content-Type': "application/x-www-form-urlencoded"  # Content-Type tells what form the body takes
        }

        payload = 'grant_type=client_credentials&client_id=%s&client_secret=%s' % (client_id, client_secret)

        headers = {
            'Content-Type': "application/x-www-form-urlencoded"
        }

        response = requests.request("POST", url, data=payload, headers=headers)
        if response.status_code == 200:
            authorization = (response.json()['access_token'])
            return authorization
        else:
            pass

    # Method to develop the Deco ment fetch API, and also if the account number is pass it will add sign on it.

    def doc_fedex_ship_data(self,token,track_id,client_url,track_info):
        URL = client_url + '/track/v1/trackingdocuments'
        # Headers for the request
        headers = {
            'Content-Type': 'application/json',
            'x-locale': 'en_US',
            'Authorization': f'Bearer {token}',  # Use the actual token
        }

        trackingnumber = track_info['trackingNumber']
        carrierCode = track_info['carrierCode']
        trackingNumberUniqueId = track_info['trackingNumberUniqueId']
        if track_id.account_no:
            account = track_id.account_no
        else:
            account = " "
        # Payload for the tracking documents request
        payload = {
            "trackDocumentDetail": {
                "documentType": "SIGNATURE_PROOF_OF_DELIVERY",

            },
            "trackDocumentSpecification": [
                {
                    "trackingNumberInfo": {
                        "trackingNumber": trackingnumber,
                        "carrierCode": carrierCode,
                        "trackingNumberUniqueId": trackingNumberUniqueId

                    },
                    "accountNumber": account
                }
            ]
        }

        response = requests.post(URL, headers=headers, json=payload)

        if response.status_code == 200:
            docs_records = response.json()
            file = docs_records['output']['documents']
            val = {
                'file' : file
            }
            return val
        else:
            print('Payload Error!')

 # Method for convert the date time getting from fedex to table format.

    def convert_date(self,dt):
        parsed_date = parser.isoparse(dt)
        naive_date = parsed_date.replace(tzinfo=None)
        return naive_date

    def update_picking(self,ship_id):
        if ship_id.picking_tracking_line:
            lst = []
            for track_id in ship_id.picking_tracking_line:
                lst.append(track_id.status)

            if len(set(lst)) == 1:
                ship_id.write({'shipped':True})
            return ship_id

    def track_fedex_ship_rout(self):
        token = self.getBearerAuthorization()
        ship_ids = self.env['stock.picking'].search([('shipped','=',False),('add_track_no','=',True)])
        for ship_id in ship_ids:
            for track_id in ship_id.picking_tracking_line:
                if track_id.delivered == False:
                    # carrier_id = self.env['delivery.carrier'].search([('id', '=', track_id.carrier_id.id)])
                    # client_url = carrier_id.tracking_client_url
                    client_url = 'https://apis.fedex.com'
                    track_url = client_url + "/track/v1/trackingnumbers"
                    trackingNumber = track_id.track_no
                    if trackingNumber:
                        payload = {
                            "trackingInfo": [
                                {
                                    "trackingNumberInfo": {
                                        "trackingNumber": trackingNumber.strip()
                                    }
                                }
                            ],
                            "includeDetailedScans": True
                        }

                        headers = {
                            'Content-Type': "application/json",
                            'X-locale': "en_US",
                            'Authorization': f'Bearer {token}',
                        }

                        payload = json.dumps(payload)
                        # date_format = '%Y-%m-%dT%H:%M:%S%z'
                        response = requests.post(track_url, data=payload, headers=headers)

                        if response.status_code == 200:
                            track_records = response.json()
                            data = track_records['output']['completeTrackResults'][0]['trackResults'][0]
                            track_info = data['trackingNumberInfo']
                            if data['latestStatusDetail']['code'] == 'DL':
                                res = self.doc_fedex_ship_data(token,track_id,client_url,track_info)
                                if 'FD' in data['trackingNumberInfo']['carrierCode']:
                                    carrier_id = self.env['delivery.carrier'].search([('name', 'ilike', 'Fedex US')])
                                track_id.write({'carrier_id':carrier_id.id, 'delivered':True,'status':data['latestStatusDetail']['description']})


                                val = {
                                    'location': data['latestStatusDetail']['scanLocation']['city']+','+data['latestStatusDetail']['scanLocation']['stateOrProvinceCode']+','+data['latestStatusDetail']['scanLocation']['countryName'],
                                    'from_date': self.convert_date(data['scanEvents'][0]['date']),
                                    'status':data['latestStatusDetail']['description'],
                                    'picking_id':ship_id.id,
                                    'track_no': track_records['output']['completeTrackResults'][0]['trackingNumber'],
                                    'receivedByName':data['deliveryDetails']['receivedByName'],
                                    'start_from' : data['shipperInformation']['address']['city']+','+data['shipperInformation']['address']['stateOrProvinceCode']+','+data['shipperInformation']['address']['countryCode'],
                                    'start_from_date' : self.convert_date(data['scanEvents'][12]['date']),
                                    'package_reached' : data['scanEvents'][12]['scanLocation']['city']+','+data['scanEvents'][12]['scanLocation']['stateOrProvinceCode']+','+data['scanEvents'][12]['scanLocation']['countryCode'],
                                    'package_reached_date' : self.convert_date(data['scanEvents'][7]['date']),
                                    'on_the_way3': data['scanEvents'][4]['scanLocation']['city'] + ',' +data['scanEvents'][4]['scanLocation']['stateOrProvinceCode'] + ',' +data['scanEvents'][4]['scanLocation']['countryCode'],
                                    'on_the_way_date': self.convert_date(data['scanEvents'][4]['date']),
                                    'out_for_delivery': data['scanEvents'][1]['scanLocation']['city'] + ',' +data['scanEvents'][1]['scanLocation']['stateOrProvinceCode'] + ',' +data['scanEvents'][1]['scanLocation']['countryCode'],
                                    'out_for_delivery_date': self.convert_date(data['scanEvents'][2]['date']),
                                    'delivered': data['scanEvents'][0]['scanLocation']['city'] + ',' +data['scanEvents'][0]['scanLocation']['stateOrProvinceCode'] + ',' +data['scanEvents'][0]['scanLocation']['countryCode'],
                                    'delivered_date': self.convert_date(data['scanEvents'][0]['date']),
                                }
                                if res:
                                    val.update(res)
                                else:
                                    pass
                            else:
                                if 'FD' in data['trackingNumberInfo']['carrierCode']:
                                    carrier_id = self.env['delivery.carrier'].search([('name', 'ilike', 'Fedex US')])
                                track_id.write({'carrier_id':carrier_id.id ,'status':data['latestStatusDetail']['description']})

                                val = {
                                    'location': data['originLocation']["locationContactAndAddress"]['address']['city'] + ',' + data['originLocation']["locationContactAndAddress"]['address']['stateOrProvinceCode'] + ',' + data['originLocation']["locationContactAndAddress"]['address']['countryName'],
                                    'from_date': self.convert_date(data['scanEvents'][0]['date']),
                                    'status': data['latestStatusDetail']['description'],
                                    'picking_id': ship_id.id,
                                    'track_no': track_records['output']['completeTrackResults'][0]['trackingNumber']
                                }

                            res = self.env['tracking.details'].search([('picking_id', '=', ship_id.id), ('status', '=', val['status']),('track_no','=',val['track_no'])])
                            if res:
                                pass
                            else:
                                if data['latestStatusDetail']['code'] == 'DL':
                                    mystring = val['file'][0]
                                    file = mystring.encode('utf-8')

                                    attachment = self.env['ir.attachment'].create({
                                        'name': 'FedEx_Shipment Document.pdf',  # Static filename
                                        'type': 'binary',
                                        'datas': file,
                                        'mimetype': 'application/pdf'
                                    })

                                    self.env['tracking.details'].create({
                                        'track_no': val['track_no'],
                                        'status':val['status'],
                                        'location':val['location'],
                                        'from_date': val['from_date'],
                                        'picking_id': val['picking_id'],
                                        'receivedByName' :val['receivedByName'],
                                        'start_from':val['start_from'],
                                        'start_from_date':val['start_from_date'],
                                        'package_reached':val['package_reached'],
                                        'package_reached_date':val['package_reached_date'],
                                        'on_the_way3':val['on_the_way3'],
                                        'on_the_way_date':val['on_the_way_date'],
                                        'out_for_delivery':val['out_for_delivery'],
                                        'out_for_delivery_date':val['out_for_delivery_date'],
                                        'delivered':val['delivered'],
                                        'delivered_date':val['delivered_date'],
                                        'attachment_id': attachment.id,
                                    })
                                else:
                                    self.env['tracking.details'].create({
                                        'track_no': val['track_no'],
                                        'status': val['status'],
                                        'location': val['location'],
                                        'from_date': val['from_date'],
                                        'picking_id': val['picking_id'],
                                    })

                    else:
                        print('PayLoad Error!')
            self.update_picking(ship_id)

    @api.constrains('picking_tracking_line')
    def _check_exist_track_line(self):
        for rec in self:
            track_no_in_lines = rec.mapped('picking_tracking_line.track_no')
            for track in track_no_in_lines:
                lines_count = len(rec.picking_tracking_line.filtered(lambda line: line.track_no == track))
                if lines_count > 1:
                    raise ValidationError(_('You cannot add same track No in line items'))


class FedextrackLine(models.Model):
    _name = 'fedex.track.line'

    picking_id = fields.Many2one('stock.picking')
    track_no = fields.Char('Tracking Number')
    carrier_id = fields.Many2one('delivery.carrier',string='Carrier')
    current_status = fields.Char('Current Status')
    file = fields.Binary('Proof Docs')
    attachment_id = fields.Many2one('ir.attachment', string="Attachment")
    delivered = fields.Boolean('Delivered')
    status = fields.Char('Current Status')
    account_no = fields.Char('Account Number')



