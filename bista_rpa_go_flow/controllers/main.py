from odoo import http, _
from odoo.http import request
import logging
from datetime import datetime

_logger = logging.getLogger(__name__)


class OdooPackageInfo(http.Controller):

    @http.route('/update_packaging_status_update', type='json',
                auth="api_key", methods=['POST'], csrf=False)
    def update_packing_update_status(self, **kwargs):
        try:
            received_data = http.request.get_json_data()
            order_ref = received_data.get('order_ref')
            status = received_data.get('status')
            log = received_data.get('log')
            if order_ref and status:
                go_flow_update_log_id = request.env['go.flow.packaging.update.log'].sudo().search(
                    [('order_ref', '=', order_ref)])
                if go_flow_update_log_id:
                    go_flow_update_log_id.sudo().update({'request_status': status, 'log': log})
                    if status == 'doc_generated_not_uploaded':
                        print("DO ALTERNATE PROCESS")
                    elif status == 'require_manual_shipment':
                        go_flow_update_log_id.picking_id.sudo().update({'goflow_routing_status': status})
                    response_data = {'status_code': 202,
                                     'status': 'success',
                                     'message': f'Updated Status for {order_ref}'
                                     }
                    return response_data
                else:
                    response_data = {'status_code': 407,
                                     'status': 'failed',
                                     'message': f'Log not found for ref {order_ref}'
                                     }
                    return response_data
        except Exception as e:
            return {'status_code': 400,
                    'status': 'error',
                    'message': str(e)
                    }
