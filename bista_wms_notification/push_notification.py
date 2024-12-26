from odoo import api, fields, models, _
from odoo.exceptions import UserError
import base64
import json
import requests
import logging

try:
    from google.oauth2 import service_account
    from google.auth.transport import requests as google_requests
except ImportError:
    service_account = None

_logger = logging.getLogger(__name__)

def firebase_send_notification(self, data, token):

    try:
        IrConfigParameter = self.env['ir.config_parameter'].sudo()
        firebase_project_id = IrConfigParameter.get_param('bista_wms_notification.firebase_project_id')
        firebase_admin_key_file = IrConfigParameter.get_param('bista_wms_notification.firebase_admin_key_file')

        if not firebase_project_id or not firebase_admin_key_file:
            _logger.exception("Some firebase configuration is missing from the settings.")
            return False

        if service_account:
            firebase_data = json.loads(
                base64.b64decode(firebase_admin_key_file).decode())
            firebase_credentials = service_account.Credentials.from_service_account_info(
                firebase_data,
                scopes=['https://www.googleapis.com/auth/firebase.messaging']
            )
            firebase_credentials.refresh(google_requests.Request())
            auth_token = firebase_credentials.token

            response = requests.post(
                f'https://fcm.googleapis.com/v1/projects/{firebase_project_id}/messages:send',
                json={
                    'message': {
                        "token": token,
                        "data": data
                    }
                },
                headers={'authorization': f'Bearer {auth_token}'},
                timeout=5
            )
            return json.loads(response.text)
        else:
            _logger.exception('You have to install'
                              '"google_auth>=1.18.0" to be able to send push '
                              'notifications.')
            return False
    except Exception as e:
        _logger.exception("Error while sending notification: %s" % e)
