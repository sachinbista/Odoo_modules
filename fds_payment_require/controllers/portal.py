# -*- coding: utf-8 -*-
import binascii

from odoo import fields, http, SUPERUSER_ID, _
from odoo.exceptions import AccessError, MissingError, ValidationError

from odoo.http import request

from odoo.addons.portal.controllers.mail import _message_post_helper
from odoo.addons.portal.controllers import portal



class CustomCustomerPortal(portal.CustomerPortal):


    @http.route(['/my/orders/<int:order_id>/accept'], type='json', auth="public", website=True)
    def portal_quote_accept(self, order_id, access_token=None, name=None, signature=None,default_po=None):
        access_token = access_token or request.httprequest.args.get('access_token')
        try:
            order_sudo = self._document_check_access('sale.order', order_id, access_token=access_token)
        except (AccessError, MissingError):
            return {'error': _('Invalid order.')}

        if not order_sudo._has_to_be_signed():
            return {'error': _('The order is not in a state requiring customer signature.')}
        if not signature:
            return {'error': _('Signature is missing.')}
        if order_sudo.partner_id.customer_po_required and not default_po:
            return {'error': _('Customer PO is missing.')}

        try:
            order_sudo.write({
                'signed_by': name,
                'signed_on': fields.Datetime.now(),
                'signature': signature,
                'client_order_ref':default_po,
            })
            request.env.cr.commit()
        except (TypeError, binascii.Error) as e:
            return {'error': _('Invalid signature data.')}
        if order_sudo.payment_term_id.payment_require:
            order_sudo.fds_payment_require = True

        if not order_sudo._has_to_be_paid() and not order_sudo.fds_payment_require:
            order_sudo.action_confirm()
            order_sudo._send_order_confirmation_mail()

        pdf = request.env['ir.actions.report'].sudo()._render_qweb_pdf('sale.action_report_saleorder', [order_sudo.id])[0]

        _message_post_helper(
            'sale.order',
            order_sudo.id,
            _('Order signed by %s', name),
            attachments=[('%s.pdf' % order_sudo.name, pdf)],
            token=access_token,
        )

        query_string = '&message=sign_ok'
        if order_sudo._has_to_be_paid(True):
            query_string += '#allow_payment=yes'
        return {
            'force_refresh': True,
            'redirect_url': order_sudo.get_portal_url(query_string=query_string),
        }