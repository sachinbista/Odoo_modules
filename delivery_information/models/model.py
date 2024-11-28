from odoo import api, models, fields, _
import requests
import csv
from dotenv import load_dotenv


client_url = "https://apis-sandbox.fedex.com"

class ProviderFedex(models.Model):
    _inherit = 'delivery.carrier'

    track_client_id = fields.Char('Tracking Cleint ID',help="To pass tracking client id",groups="base.group_system")
    track_client_secret = fields.Char('Tracking Cleint Secret',help="To pass tracking client secret",groups="base.group_system")
    tracking_client_url = fields.Char('Tracking Client Url',groups="base.group_system")

class TrackingDetails(models.Model):
    _name = 'tracking.details'

    track_no = fields.Char('Track No')
    status = fields.Char('Status')
    location = fields.Char('Location')
    from_date = fields.Datetime('Date & Time')
    picking_id = fields.Many2one('stock.picking')
    file = fields.Binary('Shipment Docs',filename="Delivery")
    attachment_id = fields.Many2one('ir.attachment', string="Attachment")
    receivedByName = fields.Char('Received By')
    start_from = fields.Char('From')
    start_from_date = fields.Char('Date')
    package_reached = fields.Char('We have your package ')
    package_reached_date = fields.Char('Date')
    on_the_way3 = fields.Char('On the way')
    on_the_way_date = fields.Char('Date')
    out_for_delivery = fields.Char('Out For Delivery')
    out_for_delivery_date = fields.Char('Date')
    delivered = fields.Char('Delivered')
    delivered_date = fields.Char('Date')
    dest_location = fields.Char('Destination Location')

    #UPS fields

    label_date = fields.Datetime('Label Date')







