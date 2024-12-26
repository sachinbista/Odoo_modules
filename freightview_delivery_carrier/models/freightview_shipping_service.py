# -*- coding: utf-8 -*-
#################################################################################
#
#    Copyright (c) 2017-Present Webkul Software Pvt. Ltd. (<https://webkul.com/>)
#    You should have received a copy of the License along with this program.
#    If not, see <https://store.webkul.com/license.html/>
#################################################################################

from odoo import api, fields, models
import logging
from odoo.exceptions import UserError, ValidationError

from . import freightview_api

_logger = logging.getLogger(__name__)
import datetime


FreightviewActivity =[
    ('draft', 'DRAFT'),
    ('pending', 'PENDING'),
    ('awarded', 'AWARDED'),
    ('confirmed', 'CONFIRMED'),
    ('picked-up', 'PICKED-UP'),
    ('delivered', 'DELIVERED'),
    ('canceled', 'CANCELED'),
]

FreightviewShipmentType =[
    ('ltl', 'LTL'),
    ('parcel', 'PARCEL'),
]

FreightviewType = [    
("business dock","business dock"),
("business no dock","business no dock"), 
("residential","residential"), 
("limited access","limited access"), 
("trade show","trade show"), 
("construction","construction"), 
("farm","farm"),
("military","military"), 
("airport","airport"), 
("place of worship","place of worship"), 
("school","school"), 
("mine","mine"), 
("pier","pier"),    
]

FreightviewClass = [
("50","50"),
("60","60"),
("65","65"),
("70","70"),
("77.5","77.5"),
("85","85"),
("92.5","92.5"),
("100","100"),
("110","110"),
("125","125"),
("150","150"),
("175","175"),
("200","200"),
("250","250"),
("300","300"),
("400","400"),
("500","500"),
]
class freightviewCarrierCodes(models.Model):
    _name="freightview.carrier.code"
    _description = "Freightview Carrier Codes"

    code = fields.Char(string='Carrier Code')
    name = fields.Char(string='Carrier Name')



class ProductPackageInherit(models.Model):
    _inherit = 'product.package'

    delivery_type = fields.Selection(selection_add=[('freightview', 'Freightview')], ondelete={'freightview': 'cascade'})



class ProductPackagingInherit(models.Model):
    _inherit = 'stock.package.type'

    package_carrier_type = fields.Selection(selection_add=[('freightview', 'Freightview')], ondelete={'freightview': 'cascade'})


class DelivertCarrierInherit(models.Model):
    _inherit = "delivery.carrier"

    delivery_type = fields.Selection(selection_add=[('freightview', 'Freightview')], ondelete={'freightview': 'set default'})
    freightview_client_id = fields.Char(string='Client ID')
    freightview_client_secret = fields.Char(string='Client Secret')
    freightview_user_api_key = fields.Char(string='User API Key')
    freightview_account_api_key = fields.Char(string='Account API Key')

    freightview_grant_type = fields.Char(string='Grant Type', default = "client_credentials")
    freightview_bearer_token = fields.Char(string='Bearer Token')
    freightview_bearer_token_expiry = fields.Datetime('Bearer Token Fetch Date')

    freightview_carrier_ids = fields.Many2many(comodel_name='freightview.carrier.code', string ="Freightview Carrier Codes")
    # TODO need to discuss workflow when selecting multiple carriers. For now biz flow is according to single carrier 
    # freightview_carrier_id = fields.Many2one(comodel_name='freightview.carrier.code', string ="Freightview Carrier")
    freightview_timeout=fields.Integer(string="Timeout", default=30)
    freightview_origin_type = fields.Selection(selection=FreightviewType, string="Freightview Origin Type", default='business dock')
    freightview_destination_type = fields.Selection(selection=FreightviewType, string="Freightview Destination Type", default='business dock')
    # freightview_charges = fields.Selection(selection=FreightviewCharges, string="Freightview Charges")
    freightClass = fields.Selection(selection=FreightviewClass, string="Freightview Class", default="50")
    


class StockPickingInherit(models.Model):
    _inherit = 'stock.picking'

    def get_all_wk_carriers(self):
        res = super(StockPickingInherit, self).get_all_wk_carriers()
        res.append('freightview')
        return res
    
    freightview_rate_url = fields.Char(string="Shipment Booking URL")
    freightview_doc_url = fields.Char(string="Shipment Documents URL")
    freightview_shipmentDetailsUrl = fields.Char(string="Freightview Shipment Details URL")
    freightview_shipment_id = fields.Char(string="Shipment Booking ID")
    freightview_pickup_status = fields.Char(string='Pickup Status')
    freightview_tracking_status = fields.Char(string='Tracking Status')
    freightview_activity_status = fields.Selection(selection=FreightviewActivity, string="Freightview Activity Status", default='draft')
    freightview_shipment_type = fields.Selection(selection=FreightviewShipmentType, string="Freightview Shipment Type", default='ltl')


    def action_get_freightview_bookUrl(self):
        if not self.has_packages:
            raise UserError('Please create packages before proceeding!')
        
        delivery_obj=self.carrier_id
        currency_id = delivery_obj.get_shipment_currency_id(pickings=self)
        currency_code = currency_id.name
        config = delivery_obj.wk_get_carrier_settings(
                ['freightview_client_id', 'freightview_client_secret', 'freightview_user_api_key','freightview_account_api_key','freightview_grant_type','freightview_timeout', 'prod_environment'])
            
        config['freightview_enviroment'] = 'production' if config['prod_environment'] else 'test'
        config['freightview_currency'] = currency_code
        config['freightview_shipment_type'] = self.freightview_shipment_type

        sdk = freightview_api.FreightviewAPI(**config)
        auth_header = sdk.get_freightview_auth_header(config.get("freightview_account_api_key"))
        if not delivery_obj.freightview_carrier_ids:
            raise UserError(f'ERROR: No carrier set for this freightview delivery method!')
        query_param = sdk.get_freightview_query_params(delivery_obj, delivery_obj.freightview_timeout or 30)
        request_body = delivery_obj.get_freightview_request_body(sdk, self, currency_code)
        freightview_book_url = sdk.get_freightview_book_url(auth_header, query_param, request_body)
        # _logger.info(f'---------freightview_book_url-----------------------------{freightview_book_url}------------------')
        temp_list  = freightview_book_url.split('/')
        # raise UserError(freightview_book_url)
        temp_index = temp_list.index('rates')
        shipment_id = temp_list[int(temp_index)+1]
        self.write({"freightview_rate_url":freightview_book_url,
                    "freightview_shipment_id":shipment_id,
                    "freightview_activity_status":"pending"
                    })

        return{
            'name' : "Redirect to freightview booking url",
            'type' : 'ir.actions.act_url',
            'url'  : freightview_book_url,
            'target' : 'new',
        }



    def action_get_freightview_shipping_detail(self):
        delivery_obj=self.carrier_id

        if True:
            result = {'exact_price': 0, 'weight': 0, 'date_delivery': None, 'tracking_number': '', 'attachments': []}
            currency_id = delivery_obj.get_shipment_currency_id(pickings=self)
            currency_code = currency_id.name
            config = delivery_obj.wk_get_carrier_settings(
                    ['freightview_client_id', 'freightview_client_secret', 'freightview_user_api_key','freightview_account_api_key','freightview_grant_type','freightview_timeout', 'prod_environment'])
                
            config['freightview_enviroment'] = 'production' if config['prod_environment'] else 'test'
            config['freightview_currency'] = currency_code
            sdk = freightview_api.FreightviewAPI(**config)

            if not delivery_obj.freightview_bearer_token or delivery_obj.freightview_bearer_token_expiry < datetime.datetime.now():
                bearer_token_result = sdk.get_freightview_bearer_token()
                delivery_obj.write({
                    "freightview_bearer_token" : bearer_token_result.get('access_token'),
                    "freightview_bearer_token_expiry" :datetime.datetime.now() + datetime.timedelta(0,int(bearer_token_result.get('expires_in')))
                })

            shipment_details_response = sdk.get_freightview_shipment_details(self.freightview_shipment_id,delivery_obj.freightview_bearer_token)
            _logger.info(f'-----shipment_details_response----------{shipment_details_response}-----------------')
            _logger.info(f'-------shipment_details_response.get("status")-------------{shipment_details_response.get("status")}----')
            if not shipment_details_response.get("status"):
                name = shipment_details_response.get('name')
                message = shipment_details_response.get('message')
            
                raise UserError(f'Freightview Error! {name} : {message}. Please create a shipment using rate url - {self.freightview_rate_url}')
            
            if shipment_details_response.get("status") == "canceled":
                self.write({
                    "freightview_activity_status" : shipment_details_response.get('status')
                })
                a = self.action_cancel()
                self.message_post(body=f"This shipment has been canceled. Please contact Freightview. For details visit {shipment_details_response.get('shipmentDetailsUrl')}")
            
            else:
                self.write({"freightview_activity_status" : shipment_details_response.get('status')})
                                    
                if not shipment_details_response.get('documents'):
                      raise UserError(f'Status: {shipment_details_response.get("status")} - Your booking has not been confirmed by Freightview. Please visit - {self.freightview_rate_url}')

                if not self.freightview_doc_url or shipment_details_response.get('documents') and shipment_details_response.get('documents')[0].get("url") and self.freightview_doc_url !=  shipment_details_response['documents'][0].get("url"):
                        self.write({
                            "freightview_doc_url" : shipment_details_response['documents'][0].get("url")
                            })
                        self.message_post(body=f"Your freightview shipment has been created. Please visit the link to download the freightview documents: {shipment_details_response['documents'][0].get('url')}")

                if not self.freightview_shipmentDetailsUrl:
                    self.write({"freightview_shipmentDetailsUrl" : shipment_details_response.get("shipmentDetailsUrl")})
                if shipment_details_response.get('tracking'):
                    self.write({"freightview_tracking_status" : shipment_details_response['tracking'].get("status")})
                result['exact_price'] = shipment_details_response['selectedQuote'].get("amount")
                result['currency'] = shipment_details_response['selectedQuote'].get("currency")
                result['weight'] = shipment_details_response['equipment'].get("weight")
                if shipment_details_response.get('pickup'):
                    self.write({"freightview_pickup_status" : shipment_details_response['pickup'].get("status")})            
                if self.freightview_activity_status == "delivered":
                    self.with_context(freightview_result=result).sudo().button_validate()

        return result
    
    

    def evaulate_freightview_shipping_cron(self,*args):
        limit = int(args[1]) or 10
        pending_freightview_pickings = self.sudo().search([("delivery_type","=","freightview"),("state","=","assigned"),("freightview_activity_status","not in",["draft"])],limit=limit)
        for pickings in pending_freightview_pickings:
            if pickings.freightview_shipmentDetailsUrl:
                pickings.action_get_freightview_shipping_detail()
