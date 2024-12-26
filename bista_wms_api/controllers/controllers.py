# -*- coding: utf-8 -*-
import json
import logging
import functools
from collections import defaultdict

from odoo import http
from odoo.exceptions import AccessDenied, AccessError
from odoo.http import request, content_disposition, serialize_exception as _serialize_exception
from odoo.addons.bista_wms_api.common import invalid_response, valid_response, convert_data_str
from odoo.tools.safe_eval import safe_eval, time
from odoo.tools import html_escape
from odoo.addons.web.controllers.main import ReportController
from datetime import datetime
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT

import werkzeug.wrappers
from werkzeug.urls import url_encode, url_decode, iri_to_uri

import werkzeug.wrappers

_logger = logging.getLogger(__name__)


def filter_by_last_sync_time(model_name, payload_data):
    """
    Filter based on last_sync_time.
    """
    id_list = []
    domain = ['|', ("create_date", ">=", payload_data['last_sync_time']),
              ("write_date", ">=", payload_data['last_sync_time'])]

    if model_name == 'stock.picking.batch' or model_name == 'stock.picking':
        model_obj = request.env[model_name].sudo().search([])
        if model_name == 'stock.picking.batch':
            for val in model_obj:
                picking_ids = val.picking_ids.filtered(
                    lambda x: x.write_date >= datetime.strptime(payload_data['last_sync_time'],
                                                                '%Y-%m-%dT%H:%M:%S.%f') or x.create_date >= datetime.strptime(
                        payload_data['last_sync_time'], '%Y-%m-%dT%H:%M:%S.%f'))
                if picking_ids and val.id not in id_list:
                    id_list.append(val.id)

        for val in model_obj:
            move_ids = val.move_ids.filtered(
                lambda x: x.write_date >= datetime.strptime(payload_data['last_sync_time'],
                                                            '%Y-%m-%dT%H:%M:%S.%f') or x.create_date >= datetime.strptime(
                    payload_data['last_sync_time'], '%Y-%m-%dT%H:%M:%S.%f'))
            if move_ids and val.id not in id_list:
                id_list.append(val.id)

        for val in model_obj:
            move_line_ids = val.move_line_ids.filtered(
                lambda x: x.write_date >= datetime.strptime(payload_data['last_sync_time'],
                                                            '%Y-%m-%dT%H:%M:%S.%f') or x.create_date >= datetime.strptime(
                    payload_data['last_sync_time'], '%Y-%m-%dT%H:%M:%S.%f'))
            if move_line_ids and val.id not in id_list:
                id_list.append(val.id)

    if id_list:
        domain += [('id', 'in', id_list)]

    return domain


def validate_token(func):
    """."""

    @functools.wraps(func)
    def wrap(self, *args, **kwargs):
        """."""
        access_token = request.httprequest.headers.get("access_token")
        if not access_token:
            return invalid_response("access_token_not_found", "missing access token in request header", 200)
        access_token_data = (
            request.env["api.access_token"].sudo().search([("token", "=", access_token)], order="id DESC", limit=1)
        )

        if access_token_data.find_one_or_create_token(user_id=access_token_data.user_id.id) != access_token:
            return invalid_response("access_token", "token seems to have expired or invalid", 200)

        request.session.update(user=access_token_data.user_id.id)
        request.update_env(user=access_token_data.user_id.id)
        return func(self, *args, **kwargs)

    return wrap


class BistaWmsApi(http.Controller):
    """Warehouse Management System Controller"""

    @staticmethod
    def _get_user_stock_group(self):
        access_token = request.httprequest.headers.get("access-token")
        if access_token:
            user_id = request.env['api.access_token'].sudo().search([('token', '=', access_token)], limit=1).user_id
            is_admin = 0
            if user_id.has_group('stock.group_stock_manager'):
                is_admin = 1
            return user_id, is_admin
        return False

    @staticmethod
    def auth_login_response_data(data):

        response_data = {
            **{
                "status": True,
                "count": len(data) if not isinstance(data, str) else 1,
            },
            **data
        }

        return response_data

    @http.route("/api/auth/login", methods=["GET", "POST"], type="json", auth="none", csrf=False)
    def auth_login(self, **post):
        """The token URL to be used for getting the access_token.

        str post[db]: db of the system, in which the user logs in to.

        str post[login]: username of the user

        str post[password]: password of the user

        :param list[str] str post: **post must contain db, login and password.
        :returns: https response
            if failed error message in the body in json format and
            if successful user's details with the access_token.
        """
        _token = request.env["api.access_token"]
        params = ["db", "login", "password"]
        req_data = json.loads(request.httprequest.data.decode())  # convert the bytes format to dict format
        req_params = {key: req_data.get(key) for key in params if req_data.get(key)}
        db, username, password = (
            req_params.get("db"),
            req_params.get("login"),
            req_params.get("password"),
        )
        _credentials_includes_in_body = all([db, username, password])
        if not _credentials_includes_in_body:
            # The request post body is empty the credentials maybe passed via the headers.
            headers = request.httprequest.headers
            db = headers.get("db")
            username = headers.get("login")
            password = headers.get("password")
            _credentials_includes_in_headers = all([db, username, password])
            if not _credentials_includes_in_headers:
                # Empty 'db' or 'username' or 'password:
                return invalid_response(
                    "missing error", "Either of the following are missing [db, username,password]", 200,
                )
        # Login in odoo database:
        session_info = []
        try:
            request.session.authenticate(db, username, password)
            session_info = request.env['ir.http'].session_info().get('server_version_info', [])
        except AccessError as aee:
            return invalid_response("Access error", "Error: %s" % aee.name)
        except AccessDenied as ade:
            return invalid_response("Access denied", "Login, password or db invalid")
        except Exception as e:
            # Invalid database:
            info = "The database name is not valid {}".format(e)
            error = "invalid_database"
            _logger.error(info)
            return invalid_response(typ=error, message=info, status=200)

        uid = request.session.uid
        # odoo login failed:
        if not uid:
            info = "authentication failed"
            error = "authentication failed"
            _logger.error(info)
            return invalid_response(status=200, typ=error, message=info)

        # Generate tokens
        access_token = _token.find_one_or_create_token(user_id=uid, create=True)
        warehouse_id = request.env.user.warehouse_id
        product_packaging = request.env.user.has_group('product.group_stock_packaging')
        product_packages = request.env.user.has_group('stock.group_tracking_lot')

        data = {
            "uid": uid,
            "user_context": convert_data_str(dict(request.env.context)) if uid else {},
            "company_id": request.env.user.company_id.id if uid else None,
            "company_ids": convert_data_str(request.env.user.company_ids.ids) if uid else None,
            "partner_id": request.env.user.partner_id.id,
            "warehouse_id": [str(warehouse_id.id),
                             warehouse_id.name] if warehouse_id else [],
            'procurement_steps': {"delivery_steps": str(warehouse_id.reception_steps or ""),
                                  "reception_steps": str(warehouse_id.delivery_steps or "")},
            "product_packages": product_packages,
            "product_packaging": product_packaging,
            "access_token": access_token,
            "company_name": request.env.user.company_name or "",
            # "currency": request.env.user.currency_id.name,
            "country": request.env.user.country_id.name or "",
            "contact_address": request.env.user.contact_address or "",
            # "customer_rank": request.env.user.customer_rank,
            "session_info": session_info,
            "wms_licensing_key": request.env['ir.config_parameter'].sudo().get_param(
                'bista_wms_api.wms_licensing_key') or "",
        }

        response_data = self.auth_login_response_data(data)

        # response_data = {
        #     **{
        #         "status": True,
        #         "count": len(data) if not isinstance(data, str) else 1,
        #     },
        #     **data
        # }

        return werkzeug.wrappers.Response(
            status=200,
            content_type="application/json; charset=utf-8",
            headers=[("Cache-Control", "no-store"), ("Pragma", "no-cache")],
            response=json.dumps(response_data)
        )

    @validate_token
    @http.route("/api/get_product_list", type="http", auth="none", methods=["GET"], csrf=False)
    def get_product_list(self, **payload):
        """ NOTE: DEPRECATED API for now, Gets the specific time frame from request and returns product details."""

        product_template_obj = request.env['product.template']

        payload_data = payload

        product_list_data = []
        response_data = {'rest_api_flag': True}

        domain = []

        if 'last_sync_time' in payload_data and payload_data['last_sync_time']:
            domain += filter_by_last_sync_time('product.template', payload_data)

        if 'create_date' in payload_data and payload_data['create_date']:
            domain.append(('create_date', '>=', payload_data['create_date']))

        if 'write_date' in payload_data and payload_data['write_date']:
            domain.append(('write_date', '>=', payload_data['write_date']))

        products = product_template_obj.sudo().search(domain, order="id ASC")

        if products:
            for product in products:
                product_list_data.append({
                    'id': product.id,
                    'name': product.name,
                    'list_price': product.list_price,
                    'uom_id': [str(product.uom_id.id), product.uom_id.name] if product.uom_id else [],
                    'create_uid': [str(product.create_uid.id), product.create_uid.name] if product.create_uid else [],
                    'create_date': product.create_date,
                    'write_uid': [str(product.write_uid.id), product.write_uid.name] if product.write_uid else [],
                    'write_date': product.write_date,
                })
            response_data.update({'data': product_list_data})

            if response_data:
                # return valid_response(response_data)
                return valid_response(product_list_data)
            else:
                return invalid_response('not_found', 'Product data not found.')
        else:
            return invalid_response('not_found', 'No product record found.')

    @staticmethod
    def _get_picking_fields(self):
        stock_picking_type_obj = request.env['stock.picking.type'].search([])
        user_id, is_admin = self._get_user_stock_group(self)
        res = []
        # domains = {
        #     # 'count_picking_draft': [('state', '=', 'draft')],
        #     # 'count_picking_waiting': [('state', 'in', ('confirmed', 'waiting'))],
        #     'count_picking_ready': [('state', '=', 'assigned')],
        #     # 'count_picking': [('state', 'in', ('assigned', 'waiting', 'confirmed'))],
        #     # 'count_picking_late': [('scheduled_date', '<', time.strftime(DEFAULT_SERVER_DATETIME_FORMAT)),
        #     #                        ('state', 'in', ('assigned', 'waiting', 'confirmed'))],
        #     # 'count_picking_backorders': [('backorder_id', '!=', False),
        #     #                              ('state', 'in', ('confirmed', 'assigned', 'waiting'))],
        # }
        # for field in domains:
        #     data = request.env['stock.picking'].read_group(domains[field] + [
        #         ('company_id', '=', request.env.user.company_id.id),
        #         ('state', 'not in', ('done', 'cancel')),
        #         ('picking_type_id', 'in', stock_picking_type_obj.ids)
        #     ], ['picking_type_id'], ['picking_type_id'])
        #     count = {
        #         # stock_picking_type_obj.browse(x['picking_type_id'][0]).name.lower().replace(" ", "_"): x['picking_type_id_count']
        #         x['picking_type_id'][0]: x['picking_type_id_count'] for x in data if x['picking_type_id']
        #     }
        #     # res.append(count)
        #     for record in stock_picking_type_obj.search([('company_id', '=', request.env.user.company_id.id)],
        #                                                 order='sequence'):
        #         # record[field] = count.get(record.id, 0)
        #         res.append({
        #             "id": record.id,
        #             "name": record.name,
        #             "code": record.code,
        #             "qty": count.get(record.id, 0),
        #             "sequence": record.sequence,
        #             # record.name.lower().replace(" ", "_"): count.get(record.id, 0)
        #         })

        # NOTE: New code for returning Ready, Waiting & Late pickings.
        if is_admin == 0:
            for record in stock_picking_type_obj.search([('company_id', '=', request.env.user.company_id.id),
                                                         ('warehouse_id', '=', user_id.warehouse_id.id)],
                                                        order='sequence'):
                res.append({
                    "id": record.id,
                    "name": record.name,
                    "code": record.code,
                    "sequence": record.sequence,
                    "count_picking_draft": record.count_picking_draft,
                    "count_picking_waiting": record.count_picking_waiting,
                    "count_picking_ready": record.count_picking_ready,
                    "count_picking_late": record.count_picking_late,
                    "count_picking": record.count_picking,
                    "count_picking_backorders": record.count_picking_backorders,
                })
        else:
            for record in stock_picking_type_obj.search([('company_id', '=', request.env.user.company_id.id)],
                                                        order='sequence'):
                res.append({
                    "id": record.id,
                    "name": record.name,
                    "code": record.code,
                    "sequence": record.sequence,
                    "count_picking_draft": record.count_picking_draft,
                    "count_picking_waiting": record.count_picking_waiting,
                    "count_picking_ready": record.count_picking_ready,
                    "count_picking_late": record.count_picking_late,
                    "count_picking": record.count_picking,
                    "count_picking_backorders": record.count_picking_backorders,
                })
        stock_picking_batch_obj = request.env['stock.picking.batch']
        batch_picking_count = stock_picking_batch_obj.search_count(
            [('state', '=', 'in_progress'), ('company_id', '=', request.env.user.company_id.id),
             ('is_wave', '=', False)])
        res.append({
            "id": 0,
            "name": "Batch Transfers",
            "code": "",
            "sequence": 0,
            "count_picking_draft": 0,
            "count_picking_waiting": 0,
            "count_picking_ready": batch_picking_count,
            "count_picking_late": 0,
            "count_picking": 0,
            "count_picking_backorders": 0,
        })

        wave_picking_count = stock_picking_batch_obj.search_count(
            [('state', '=', 'in_progress'), ('company_id', '=', request.env.user.company_id.id),
             ('is_wave', '=', True)])
        res.append({
            "id": 0,
            "name": "Wave Transfers",
            "code": "",
            "sequence": 0,
            "count_picking_draft": 0,
            "count_picking_waiting": 0,
            "count_picking_ready": wave_picking_count,
            "count_picking_late": 0,
            "count_picking": 0,
            "count_picking_backorders": 0,
        })
        return res

    @staticmethod
    def _get_dashboard_values(self):
        product_template_obj = request.env['product.template'].search([('type', 'in', ['consu', 'product'])])
        user_id, is_admin = self._get_user_stock_group(self)

        res = {}

        sum_qty_available = 0
        # sum_virtual_available = 0
        sum_incoming_qty = 0
        sum_outgoing_qty = 0
        sum_batch_picking_qty = 0
        sum_wave_picking_qty = 0

        domain = [
            ('date', '>=', datetime.now().strftime('%Y-%m-%d 00:00:00')),
            ('date', '<=', datetime.now().strftime('%Y-%m-%d 23:59:59'))
        ]

        # stock_move_line_obj = request.env['stock.move.line']
        stock_move_line_objs = request.env['stock.move.line'].search(domain)

        # sum_incoming_qty = stock_move_line_obj.search_count(
        #     domain + [('picking_id.picking_type_id.code', '=', 'incoming')]
        # )
        # sum_outgoing_qty = stock_move_line_obj.search_count(
        #     domain + [('picking_id.picking_type_id.code', '=', 'outgoing')]
        # )

        for stock_move_line_obj in stock_move_line_objs:
            # Transfers calculation
            if is_admin == 0:
                if stock_move_line_obj.sudo().picking_id.user_id.id == user_id.id:
                    if stock_move_line_obj.picking_id.picking_type_id.code == "incoming":
                        sum_incoming_qty += stock_move_line_obj.qty_done
                    elif stock_move_line_obj.picking_id.picking_type_id.code == "outgoing":
                        sum_outgoing_qty += stock_move_line_obj.qty_done
            else:
                if stock_move_line_obj.picking_id.picking_type_id.code == "incoming":
                    sum_incoming_qty += stock_move_line_obj.qty_done
                elif stock_move_line_obj.picking_id.picking_type_id.code == "outgoing":
                    sum_outgoing_qty += stock_move_line_obj.qty_done

            # Batch & Wave Pickings calculation
            if stock_move_line_obj.batch_id:
                if is_admin == 0:
                    if stock_move_line_obj.sudo().batch_id.user_id.id == user_id.id:
                        if not stock_move_line_obj.batch_id.is_wave:
                            sum_batch_picking_qty += stock_move_line_obj.qty_done
                        elif stock_move_line_obj.batch_id.is_wave:
                            sum_wave_picking_qty += stock_move_line_obj.qty_done
                else:
                    if not stock_move_line_obj.batch_id.is_wave:
                        sum_batch_picking_qty += stock_move_line_obj.qty_done
                    elif stock_move_line_obj.batch_id.is_wave:
                        sum_wave_picking_qty += stock_move_line_obj.qty_done

        for prod_temp in product_template_obj:
            sum_qty_available += prod_temp.qty_available
            # sum_virtual_available += prod_temp.virtual_available
            # sum_incoming_qty += prod_temp.incoming_qty
            # sum_outgoing_qty += prod_temp.outgoing_qty

        res.update({
            'sum_qty_available': sum_qty_available,
            # 'sum_virtual_available': sum_virtual_available,
            'sum_incoming_qty': sum_incoming_qty,
            'sum_outgoing_qty': sum_outgoing_qty,
            'sum_batch_picking_qty': sum_batch_picking_qty,
            'sum_wave_picking_qty': sum_wave_picking_qty,
        })

        res.update({"to_process_count": self._get_picking_fields(self)})
        res.update({"warehouse_id": [str(user_id.warehouse_id.id),
                                     user_id.warehouse_id.name] if user_id.warehouse_id else []})
        res.update({"wms_licensing_key": request.env['ir.config_parameter'].sudo().get_param(
            'bista_wms_api.wms_licensing_key') or ""})

        # Pass 'quality_modules_installed' as False by default to be changed in inherited function later.
        res.update({'quality_modules_installed': False})

        return res

    @validate_token
    @http.route("/api/get_dashboard_today_stock_and_receipt", type="http", auth="none", methods=["GET"], csrf=False)
    def get_dashboard_today_stock_and_receipt(self, **payload):
        """Get Stock, Transfers & Receipt for Current Date for Dashboard."""

        _logger.info("/api/get_dashboard_today_stock_and_receipt payload: %s", payload)

        try:
            res = self._get_dashboard_values(self)

            return valid_response(res)
        except Exception as e:
            _logger.exception("Error while getting stock, transfers & receipt of dashboard for payload: %s", payload)
            error_msg = 'Error while getting stock, transfers & receipt of dashboard.'
            return invalid_response('bad_request', error_msg, 200)

    @validate_token
    @http.route("/api/get_picking_move_ids", type="http", auth="none", methods=["GET"], csrf=False)
    def get_picking_move_ids(self, **payload):
        """
            NOTE: DEPRECATED API for now, might be used later on.
            Gets the name of a stock_picking record from request and
            returns that specific stock_picking record's operations details.
            @:param barcode
            @:returns only the stock.move records related to the stock.picking record.
        """

        response_data = {}
        payload_data = payload

        if 'barcode' in payload_data:
            if payload_data['barcode']:
                stock_picking_obj = request.env['stock.picking'].sudo().search(
                    [('name', '=', payload_data.get('barcode'))])
                if stock_picking_obj:
                    move_ids = stock_picking_obj.move_ids_without_package.sudo().read(
                        ['name', 'product_uom_qty', 'quantity_done'])
                    response_data.update({
                        'id': stock_picking_obj.id,
                        'name': stock_picking_obj.name,
                        'move_ids': move_ids
                    })
                    return valid_response(response_data)
                else:
                    return invalid_response('not_found', 'No Picking record found.')
            else:
                return invalid_response('not_found', 'No barcode was provided.', 200)
        else:
            # ToDo: return all data in Ready state instead of invalid_response()
            return invalid_response('not_found', 'No barcode was provided.', 200)

    @staticmethod
    def get_picking_detail_response_data(self, response_data, stock_picking_objs):
        for stock_picking_obj in stock_picking_objs:
            move = []
            move_line = []
            sale_id = stock_picking_obj.sale_id.id if stock_picking_obj.sale_id else 0
            purchase_id = stock_picking_obj.purchase_id.id if stock_picking_obj.purchase_id else 0
            rfid_tag = stock_picking_obj.rfid_tag.name if 'rfid_tag' in stock_picking_obj._fields else ""
            for move_id in stock_picking_obj.move_ids_without_package:
                move.append({
                    'id': move_id.id,
                    'product_id': move_id.product_id.id,
                    'product': move_id.product_id.display_name,
                    'location_id': [str(move_id.location_id.id),
                                    move_id.location_id.complete_name] if move_id.location_id else [],
                    "product_packaging": [str(move_id.product_packaging_id.id),
                                          move_id.product_packaging_id.name] if move_id.product_packaging_id else [],
                    'product_code': move_id.product_id.default_code or "",
                    'description_picking': move_id.description_picking or "",
                    'product_uom_qty': move_id.product_uom_qty,
                    'state': dict(move_id._fields['state'].selection).get(move_id.state),
                })

            # move_ids = stock_picking_obj.move_ids_without_package.read([
            #     'name', 'description_picking', 'product_uom_qty', 'state'
            # ])
            # for move_id in move_ids:
            #     move_id['state'] = dict(stock_picking_obj.move_ids_without_package._fields['state'].selection).get(move_id['state'])
            for line_id in stock_picking_obj.move_line_ids:
                quant_line = []

                stock_quants = request.env['stock.quant'].search([
                    ('product_id', '=', line_id.product_id.id), ('quantity', '>=', 0)
                ])
                product_stock_quant_ids = stock_quants.filtered(
                    lambda q: q.company_id in request.env.companies and q.location_id.usage == 'internal'
                )

                for quant_id in product_stock_quant_ids:
                    rfid = quant_id.lot_id.rfid_tag.name if 'rfid_tag' in quant_id.lot_id._fields else ""
                    quant_line.append({
                        'id': quant_id.id,
                        'location': quant_id.location_id.complete_name,
                        'lot_serial': quant_id.lot_id.name if quant_id.lot_id else "",
                        'rfid_tag': rfid or "",
                        'on_hand_quantity': quant_id.quantity,
                    })
                move_line.append({
                    'id': line_id.id,
                    'product_id': line_id.product_id.id,
                    'product': line_id.product_id.name,
                    'location_id': [str(line_id.location_id.id),
                                    line_id.location_id.complete_name] if line_id.location_id else [],
                    'product_packages': [str(line_id.result_package_id.id),
                                         line_id.result_package_id.name] if line_id.result_package_id else [],
                    'product_code': line_id.product_id.default_code or "",
                    'product_uom_qty': line_id.reserved_uom_qty,
                    'quantity_done': line_id.qty_done,
                    'quant_ids': quant_line,
                })
            # print('reception------------------',stock_picking_obj.picking_type_id.warehouse_id.reception_route_id.sequence)
            # print('reception------------------',stock_picking_obj.picking_type_id.warehouse_id.route_ids)
            # for value in stock_picking_obj.picking_type_id.warehouse_id.route_ids:
            #     print('sequence--------------',value.sequence,stock_picking_obj.name)
            # if stock_picking_obj.group_id:
            #     for value in stock_picking_obj.picking_type_id.warehouse_id.route_ids:
            #         print('sequence--------------',value.sequence,stock_picking_obj.name)
            response_data.append({
                'id': stock_picking_obj.id,
                'name': stock_picking_obj.name,
                'rfid_tag': rfid_tag or "",
                'source_doc': stock_picking_obj.origin if stock_picking_obj.origin else "",
                'schedule_date': stock_picking_obj.scheduled_date or "",
                'deadline': stock_picking_obj.date_deadline or "",
                'done_date': stock_picking_obj.date_done or "",
                'operation_type': stock_picking_obj.operation_type if stock_picking_obj.operation_type else "",
                'partner_id': [str(stock_picking_obj.partner_id.id),
                               stock_picking_obj.partner_id.name] if stock_picking_obj.partner_id else [],
                'user_id': [str(stock_picking_obj.user_id.id),
                            stock_picking_obj.user_id.name] if stock_picking_obj.user_id else [],
                'location_id': [str(stock_picking_obj.location_id.id),
                                stock_picking_obj.location_id.display_name] if stock_picking_obj.location_id else [],
                'location_dest_id': [str(stock_picking_obj.location_dest_id.id),
                                     stock_picking_obj.location_dest_id.display_name] if stock_picking_obj.location_dest_id else [],
                'operation_type_id': [str(stock_picking_obj.picking_type_id.id),
                                      stock_picking_obj.picking_type_id.name] if stock_picking_obj.picking_type_id else [],
                'warehouse_id': [str(stock_picking_obj.picking_type_id.warehouse_id.id),
                                 stock_picking_obj.picking_type_id.warehouse_id.name] if stock_picking_obj.picking_type_id.warehouse_id else [],
                'group_id': str(stock_picking_obj.group_id.id) if stock_picking_obj.group_id else "",
                'procurement_group': [str(stock_picking_obj.group_id.id),
                                      str(stock_picking_obj.group_id.name)] if stock_picking_obj.group_id else [],
                'priority': dict(stock_picking_obj._fields['priority'].selection).get(
                    stock_picking_obj.priority),
                'company': stock_picking_obj.company_id.name,
                'move_ids': move,
                'move_line_ids': move_line,
                # 'batch_id': [str(stock_picking_obj.batch_id.id or ""), stock_picking_obj.batch_id.name or ""],
                'sale_id': sale_id,
                'purchase_id': purchase_id,
                'state': stock_picking_obj.state,
                'shipping_policy': stock_picking_obj.move_type,
                'create_uid': [str(stock_picking_obj.create_uid.id),
                               stock_picking_obj.create_uid.name] if stock_picking_obj.create_uid else [],
                'create_date': stock_picking_obj.create_date,
                'write_uid': [str(stock_picking_obj.write_uid.id),
                              stock_picking_obj.write_uid.name] if stock_picking_obj.write_uid else [],
                'write_date': stock_picking_obj.write_date,
            })
        # response_data = sorted(response_data, key=lambda i: i['group_id'][0], reverse= True)
        return response_data

    @validate_token
    @http.route("/api/get_picking_detail", type="http", auth="none", methods=["GET"], csrf=False)
    def get_picking_detail(self, **payload):
        """
            Gets the name of a stock_picking record from request and
            returns that specific stock_picking record's details.
            If name of a stock_picking not in request then returns
            all the stock_picking record details of ready state.
        """

        _logger.info("/api/get_picking_detail payload: %s", payload)

        try:
            response_data = []
            payload_data = payload
            domain = []
            if 'last_sync_time' in payload_data and payload_data['last_sync_time']:
                domain += filter_by_last_sync_time('stock.picking', payload_data)

            stock_picking = request.env['stock.picking'].search(domain)
            stock_picking_objs = False
            multi_steps_routing = request.env.user.has_group('stock.group_adv_location')

            user_id, is_admin = self._get_user_stock_group(self)

            if 'barcode' in payload_data or 'picking_id' in payload_data or 'picking_type_id' in payload_data:
                # domain = [('state', '=', 'assigned')]
                if 'barcode' in payload_data:
                    if payload_data['barcode']:
                        stock_picking_domain = [('name', '=', payload_data.get('barcode'))]
                        if 'rfid_tag' in stock_picking._fields:
                            stock_picking_domain = ['|', ('name', '=', payload_data.get('barcode')),
                                                    ('rfid_tag.name', '=', payload_data.get('barcode'))]
                        if is_admin == 0:
                            stock_picking_domain = stock_picking_domain + [('user_id', '=', user_id.id)]
                        stock_picking_objs = stock_picking.sudo().search(stock_picking_domain)
                elif 'picking_id' in payload_data:
                    if payload_data['picking_id']:
                        stock_picking_domain = [
                            ('id', '=', int(payload_data['picking_id']))
                        ]
                        if is_admin == 0:
                            stock_picking_domain = stock_picking_domain + [('user_id', '=', user_id.id)]
                        stock_picking_objs = stock_picking.sudo().search(stock_picking_domain)
                elif 'picking_type_id' in payload_data:
                    if payload_data['picking_type_id']:
                        stock_picking_domain = [
                            ('state', '=', 'assigned'),
                            ('picking_type_id', '=', int(payload_data.get('picking_type_id')))
                        ]
                        if is_admin == 0:
                            stock_picking_domain = stock_picking_domain + [('user_id', '=', user_id.id)]
                        stock_picking_objs = stock_picking.sudo().search(stock_picking_domain)
            else:
                if not multi_steps_routing:
                    stock_picking_domain = [('state', '=', 'assigned'),
                                            ('company_id', '=', request.env.user.company_id.id)]
                else:
                    stock_picking_domain = [('state', 'in', ['assigned', 'waiting']),
                                            ('company_id', '=', request.env.user.company_id.id)]
                if is_admin == 0:
                    if user_id.warehouse_id.reception_steps in ['two_steps',
                                                                'three_steps'] or user_id.warehouse_id.delivery_steps in [
                        'pick_ship', 'pick_pack_ship']:
                        stock_picking_domain = stock_picking_domain + \
                                               [('user_id', '=', user_id.id)]
                    else:
                        stock_picking_domain = [('state', '=', 'assigned'), (
                            'company_id', '=', request.env.user.company_id.id), ('user_id', '=', user_id.id)]

                if 'last_sync_time' in payload_data and payload_data['last_sync_time']:
                    stock_picking_domain += filter_by_last_sync_time('stock.picking', payload_data)

                stock_picking_objs = stock_picking.sudo().search(stock_picking_domain, order='id')

            if stock_picking_objs:
                response_data = self.get_picking_detail_response_data(self, response_data, stock_picking_objs)

                return valid_response(response_data)
            else:
                return invalid_response('not_found', 'No Picking record found.')
        except Exception as e:
            _logger.exception("Error while getting picking details for payload: %s", payload)
            error_msg = 'Error while getting picking details.'
            return invalid_response('bad_request', error_msg, 200)

    @validate_token
    @http.route('/api/report/download', type='http', auth="none", methods=["GET"], csrf=False)
    def api_report_download(self, report_name=None, report_type=None, options=None, context=None):
        """This function is used by 'action_manager_report.js' in order to trigger the download of
        a pdf/controller report.

        @:param report_name: a javascript array JSON.stringified containing report internal url
        @:param report_type: a string that contains the report type to print.
        @:param options: a JSON containing the details options for printing a report.
        @:returns: Response with an attachment header

        """
        _logger.info("/api/report/download report_name: %s, report_type: %s, options: %s, context: %s",
                     report_name, report_type, options, context)
        try:
            if report_name and report_type:
                data = "[" + report_name + "," + report_type + "]"
                requestcontent = json.loads(data)
                url, type = requestcontent[0], requestcontent[1]
                reportname = '???'
                try:
                    if type in ['qweb-pdf', 'qweb-text']:
                        converter = 'pdf' if type == 'qweb-pdf' else 'text'
                        extension = 'pdf' if type == 'qweb-pdf' else 'txt'

                        pattern = '/report/pdf/' if type == 'qweb-pdf' else '/report/text/'
                        reportname = url.split(pattern)[1].split('?')[0]

                        docids = None
                        if '/' in reportname:
                            reportname, docids = reportname.split('/')

                            # NOTE: Check if the picking id exists for Picking Operation & Delivery Slip reports
                            if docids and reportname in ['stock.report_deliveryslip', 'stock.report_picking']:
                                ids = [int(x) for x in docids.split(",")]
                                stock_picking_obj = request.env['stock.picking'].search([('id', 'in', ids)])
                                if not stock_picking_obj:
                                    return invalid_response('bad_request', 'Provided picking not found.', 200)

                        if docids:
                            # Generic report:
                            response = ReportController.report_routes(self, reportname=reportname, docids=docids,
                                                                      converter=converter, context=context)
                        else:
                            # Particular report:
                            # data = dict(url_decode(url.split('?')[1]).items())  # decoding the args represented in JSON
                            # data = dict(url_decode(options).items())  # decoding the args represented in JSON
                            # data = json.loads(options)
                            if 'context' in data:
                                # context, data_context = json.loads(context or '{}'), json.loads(data.pop('context'))
                                context, data_context = json.loads(context or '{}'), json.loads(options)
                                context = json.dumps({**context, **data_context})
                            response = ReportController.report_routes(self, reportname=reportname, converter=converter,
                                                                      context=context, **json.loads(options))

                        report = request.env['ir.actions.report']._get_report_from_name(reportname)
                        filename = "%s.%s" % (report.name, extension)

                        if docids:
                            ids = [int(x) for x in docids.split(",")]
                            obj = request.env[report.model].browse(ids)
                            if report.print_report_name and not len(obj) > 1:
                                report_name = safe_eval(report.print_report_name, {'object': obj, 'time': time})
                                filename = "%s.%s" % (report_name, extension)
                        response.headers.add('Content-Disposition', content_disposition(filename))
                        return response
                    else:
                        _logger.exception("The report_type in request is not defined properly.")
                        return invalid_response('bad_request',
                                                'The report_type in request is not defined properly.', 200)
                except Exception as e:
                    _logger.exception("Error while generating report %s", reportname)
                    # se = _serialize_exception(e)
                    # error = {
                    #     'code': 200,
                    #     'message': "Odoo Server Error",
                    #     'data': se
                    # }
                    # return request.make_response(html_escape(json.dumps(error)))
                    error_message = "Error while generating report '" + reportname + "'"
                    return invalid_response('bad_request', error_message, 200)
            else:
                return invalid_response('bad_request', 'Report Name or Type was not provided.', 200)
        except Exception as e:
            _logger.exception(
                "Error while generating Report for report_name: %s, report_type: %s, options: %s, context: %s",
                report_name, report_type, options, context)
            error_msg = 'Error while generating Report.'
            return invalid_response('bad_request', error_msg, 200)

    @validate_token
    @http.route('/api/label/download', type='http', auth="none", methods=["GET"], csrf=False)
    def api_label_download(self, context=None, **payload):
        _logger.info("/api/label/download payload: %s, context: %s", payload, context)

        try:
            payload_data = payload

            if 'picking_id' in payload_data and 'batch_id' in payload_data:
                return invalid_response('bad_request', "Both Picking or Batch id should not be provided.", 200)
            elif 'picking_id' in payload_data or 'batch_id' in payload_data:
                context = json.loads(context)

                if 'picking_id' in payload_data:
                    picking_id = int(payload_data.get('picking_id'))
                    active_id = picking_id
                    stock_picking_obj = request.env['stock.picking'].sudo().browse(picking_id)
                    move_lines = stock_picking_obj.move_ids_without_package.move_line_ids

                elif 'batch_id' in payload_data:
                    batch_id = int(payload_data.get('batch_id'))
                    active_id = batch_id
                    stock_picking_batch_obj = request.env['stock.picking.batch'].sudo().browse(batch_id)
                    move_lines = stock_picking_batch_obj.move_line_ids

                stock_picking_move_lines_products = []
                for move_line in move_lines:
                    stock_picking_move_lines_products.append(move_line.product_id.id)

                if eval(payload_data.get('is_lot_label')):
                    stock_picking_move_lines_lots = []
                    for move_line in move_lines:
                        if move_line.lot_id:
                            stock_picking_move_lines_lots.append(move_line.lot_id.id)

                new_context = dict(context, **{
                    "allowed_company_ids": request.env.user.company_ids.ids,
                    "contact_display": "partner_address", "active_model": "stock.picking",
                    "active_id": active_id, "active_ids": [active_id],
                    "default_product_ids": stock_picking_move_lines_products,
                    "default_move_line_ids": move_lines.ids,
                    "default_picking_quantity": "picking"
                })

                # NOTE: create new layout wizard through code & get the id to pass in the options
                if not eval(payload_data.get('is_lot_label')):
                    prod_label_wiz = request.env['product.label.layout'].sudo().with_context(new_context).create({
                        "print_format": 'dymo',
                        "product_ids": [(6, 0, stock_picking_move_lines_products)],
                        "picking_quantity": 'picking'
                    })
                    prod_label_wiz_rec = request.env['product.label.layout'].browse(prod_label_wiz.id)
                    prod_label_wiz_process_data = prod_label_wiz_rec.with_context(context).process()
                    if prod_label_wiz_process_data.get('report_name') and prod_label_wiz_process_data.get(
                            'report_type') and prod_label_wiz_process_data.get('data'):
                        report_name = '"/report/pdf/' + prod_label_wiz_process_data['report_name'] + '"'
                        report_type = '"' + prod_label_wiz_process_data['report_type'] + '"'
                        options = prod_label_wiz_process_data['data']
                        return self.api_report_download(report_name=report_name, report_type=report_type,
                                                        options=json.dumps(options), context=json.dumps(new_context))

                if eval(payload_data.get('is_lot_label')):
                    label_quantity = payload_data.get('label_quantity').lower()
                    lot_label_wiz = request.env['lot.label.layout'].sudo().with_context(new_context).create({
                        "label_quantity": label_quantity,
                        "print_format": '4x12',
                    })
                    lot_label_wiz_rec = request.env['lot.label.layout'].browse(lot_label_wiz.id)
                    lot_label_wiz_process_data = lot_label_wiz_rec.with_context(context).process()
                    if lot_label_wiz_process_data.get('report_name') and lot_label_wiz_process_data.get(
                            'report_type') and lot_label_wiz_process_data.get('data'):
                        report_name = '"/report/pdf/' + lot_label_wiz_process_data['report_name'] + '"'
                        report_type = '"' + lot_label_wiz_process_data['report_type'] + '"'
                        all_docids = []
                        if 'batch_id' in payload_data and payload_data.get('batch_id'):
                            doc_picking_ids = request.env['stock.picking.batch'].sudo().search(
                                [('id', 'in', [batch_id])]).picking_ids
                        else:
                            doc_picking_ids = request.env['stock.picking'].sudo().search([('id', 'in', [picking_id])])
                        if doc_picking_ids and label_quantity == 'lots':
                            all_docids = doc_picking_ids.move_line_ids.lot_id.ids
                        else:
                            uom_categ_unit = request.env.ref('uom.product_uom_categ_unit')
                            quantity_by_lot = defaultdict(int)
                            for move_line in doc_picking_ids.move_line_ids:
                                if not move_line.lot_id:
                                    continue
                                if move_line.product_uom_id.category_id == uom_categ_unit:
                                    quantity_by_lot[move_line.lot_id.id] += int(move_line.qty_done)
                                else:
                                    quantity_by_lot[move_line.lot_id.id] += 1
                            docids = []
                            for lot_id, qty in quantity_by_lot.items():
                                docids.append([lot_id] * qty)
                            for val in docids:
                                all_docids += val

                        if not all_docids:
                            return invalid_response(typ='bad_request', status=200,
                                                    message="Error while generating Lot Labels. No available lot to print.")
                        options = {'all_docids': all_docids}

                    return self.api_report_download(report_name=report_name, report_type=report_type,
                                                    options=json.dumps(options), context=json.dumps(new_context))
                else:
                    return invalid_response(typ='bad_request', status=200,
                                            message="Error while generating Labels. Please contact Administrator")
            else:
                return invalid_response('bad_request', "Picking or Batch id was not provided.", 200)
        except Exception as e:
            _logger.exception("Error while generating labels for payload: %s", payload)
            # se = _serialize_exception(e)
            # _logger.exception(se)
            error_msg = 'Error while generating Product Labels.'
            # if "name" in e:
            #     error_msg += "Reason:\n" + e.name
            # error_msg = error_msg.replace('\n', ' ')
            return invalid_response('bad_request', error_msg, 200)

    @validate_token
    @http.route("/api/user_detail", type="http", auth="none", methods=["GET"], csrf=False)
    def get_user_detail(self, **payload):
        _logger.info("/api/user_detail GET payload: %s", payload)

        try:
            access_token = request.httprequest.headers.get("access-token")
            user_id = request.env['api.access_token'].sudo().search([('token', '=', access_token)], limit=1).user_id
            if user_id and request.httprequest.method == 'GET':
                user_details = {
                    'name': user_id.name or "",
                    'email': user_id.login or "",
                    'image': user_id.image_1920.decode("utf-8") if user_id.image_1920 else "",
                    "warehouse_id": [str(user_id.warehouse_id.id),
                                     user_id.warehouse_id.name] if user_id.warehouse_id else [],
                }
                # NOTE: ADD to_process_count to the User Profile
                user_details.update({"to_process_count": self._get_picking_fields(self)})
                return valid_response(user_details)
            else:
                return invalid_response('not_found', 'No User Data Found.')
        except Exception as e:
            _logger.exception("Error while getting user data for payload: %s", payload)
            error_msg = 'Error while getting user data.'
            return invalid_response('bad_request', error_msg, 200)

    @staticmethod
    def get_product_detail_response_data(self, domain, payload_data):

        product_product = request.env['product.product'].search(domain)
        stock_lot = request.env['stock.lot'].search(domain)

        if 'barcode' in payload_data:
            if payload_data['barcode']:
                # get product.product object search by barcode
                product_product_domain = [('barcode', '=', payload_data.get('barcode'))]
                if 'rfid_tag' in product_product._fields:
                    product_product_domain = ['|', ('barcode', '=', payload_data.get('barcode')),
                                              ('rfid_tag.name', '=', payload_data.get('barcode'))]
                product_product_objs = product_product.search(product_product_domain, limit=1)
                if product_product_objs:
                    product_template_objs = product_product_objs.product_tmpl_id
                    product_template_img = product_template_objs.image_1920.decode(
                        "utf-8") if product_template_objs.image_1920 else ""
                elif not product_product_objs:
                    # get product.product object from stock.production.lot
                    stock_lot_domain = [('name', '=', payload_data.get('barcode'))]
                    if 'rfid_tag' in product_product._fields:
                        stock_lot_domain = ['|', ('name', '=', payload_data.get('barcode')),
                                            ('rfid_tag.name', '=', payload_data.get('barcode'))]
                    product_product_objs = stock_lot.sudo().search(stock_lot_domain, limit=1).product_id
                    if product_product_objs:
                        product_template_objs = product_product_objs.product_tmpl_id
                        product_template_img = product_template_objs.image_1920.decode(
                            "utf-8") if product_template_objs.image_1920 else ""
                    else:
                        # return invalid_response('not_found', 'No product found for this barcode.')
                        return {"status": False, 'code': "not_found", 'message': "No product found for this barcode"}
            else:
                # return invalid_response('not_found', 'No product found for this barcode.')
                return {"status": False, 'code': "not_found", 'message': "No product found for this barcode"}
        else:
            domain.append(('type', 'in', ['consu', 'product']))
            product_template_objs = request.env['product.template'].search(domain)
            product_template_img = ""

        if product_template_objs:

            response_data = []
            stock_putaway = request.env['stock.putaway.rule']
            stock_storage_capacity = request.env['stock.storage.category.capacity']

            for product in product_template_objs:
                barcode = []
                rfid_tags = []
                packaging_line = []
                for product_variant in product.product_variant_ids:
                    if product_variant.barcode:
                        barcode.append(product_variant.barcode)
                    if 'rfid_tag' in product_variant._fields:
                        rfid_tags.append(product_variant.rfid_tag.name if product_variant.rfid_tag else "")
                stock_quants = request.env['stock.quant'].search([
                    ('product_id.product_tmpl_id', '=', product.id), ('quantity', '>=', 0),
                    ('location_id.usage', '=', 'internal'),
                    ('company_id', '=', request.env.user.company_id.id)
                ])
                stock_quants_on_hand_qty = stock_quants.mapped('quantity')
                stock_quants_available_quantity_qty = stock_quants.mapped('available_quantity')

                quant_detail = stock_quants.sudo().read([
                    'location_id', 'product_id', 'lot_id', 'package_id', 'owner_id', 'product_categ_id',
                    'quantity', 'reserved_quantity', 'available_quantity',
                    'inventory_quantity', 'inventory_quantity_auto_apply', 'inventory_diff_quantity',
                    'inventory_date'
                ])
                for quant in quant_detail:
                    if not quant['location_id']:
                        quant['location_id'] = []
                    else:
                        quant['location_id'] = list(quant['location_id'])
                        quant['location_id'][0] = str(quant['location_id'][0])
                    if not quant['product_id']:
                        quant['product_id'] = []
                    else:
                        quant['product_id'] = list(quant['product_id'])
                        quant['product_id'][0] = str(quant['product_id'][0])
                    if not quant['lot_id']:
                        quant['lot_id'] = []
                    else:
                        quant['lot_id'] = list(quant['lot_id'])
                        quant['lot_id'][0] = str(quant['lot_id'][0])
                    if not quant['package_id']:
                        quant['package_id'] = []
                    else:
                        quant['package_id'] = list(quant['package_id'])
                        quant['package_id'][0] = str(quant['package_id'][0])
                    if not quant['owner_id']:
                        quant['owner_id'] = []
                    else:
                        quant['owner_id'] = list(quant['owner_id'])
                        quant['owner_id'][0] = str(quant['owner_id'][0])
                    if not quant['product_categ_id']:
                        quant['product_categ_id'] = []
                    else:
                        quant['product_categ_id'] = list(quant['product_categ_id'])
                        quant['product_categ_id'][0] = str(quant['product_categ_id'][0])

                putaway_count = stock_putaway.sudo().search_count([
                    ('company_id', '=', request.env.user.company_id.id),
                    '|', ('product_id.product_tmpl_id', '=', product.id),
                    ('category_id', '=', product.categ_id.id)
                ])
                storage_capacity_count = stock_storage_capacity.sudo().search_count([
                    ('product_id', 'in', product.product_variant_ids.ids),
                    ('company_id', '=', request.env.user.company_id.id)
                ])
                stock_lot_obj = stock_lot.search([('product_id', 'in', product.product_variant_ids.ids)])
                lot_serial = stock_lot_obj.mapped('name')
                if 'rfid_tag' in stock_lot._fields:
                    for lot_obj in stock_lot_obj:
                        rfid_tags.append(lot_obj.rfid_tag.name if lot_obj.rfid_tag else "")
                # packaging_type details:
                user_id, is_admin = self._get_user_stock_group(self)
                packaging_enabled = user_id.has_group('product.group_stock_packaging')
                if packaging_enabled:
                    for packaging in product.packaging_ids:
                        packaging_line.append({
                            'name': packaging.name,
                            'package_type_id': [str(packaging.package_type_id.id),
                                                str(packaging.package_type_id.name)] if packaging.package_type_id else [],
                            'qty': packaging.qty,
                            'sales': str(packaging.sales or ""),
                            'purchase': str(packaging.purchase or ""),
                        })

                response_data.append({
                    'id': product.id,
                    'product_name': product.name,
                    'product_code': product.default_code or "",
                    'barcode': barcode + lot_serial + rfid_tags,
                    'prod_barcode': barcode,
                    'lot_serial_number': lot_serial,
                    'rfid_tags': rfid_tags,
                    'expiration_date': product.use_expiration_date if 'use_expiration_date' in product._fields else False,
                    'inventory_location': product.property_stock_inventory.complete_name or "",
                    'variant': product.product_variant_count,
                    'on_hand': sum(stock_quants_on_hand_qty) if stock_quants else 0,
                    'available_quantity': sum(stock_quants_available_quantity_qty) if stock_quants else 0,
                    'on_hand_details': quant_detail,
                    'purchase_unit': product.purchased_product_qty,
                    'sold_unit': product.sales_count,
                    'putaway': putaway_count,
                    'storage_capacity': storage_capacity_count,
                    'product_in': product.nbr_moves_in,
                    'product_out': product.nbr_moves_out,
                    'packaging_line': packaging_line,
                    'image': product_template_img or "",

                })

            # return valid_response(response_data)
            return {"status": True, 'data': response_data}

        else:
            # return invalid_response('not_found', 'No product found.')
            return {"status": False, 'code': "not_found", 'message': "No product found"}

    @validate_token
    @http.route("/api/get_product_detail", type="http", auth="none", methods=["GET"], csrf=False)
    def get_product_detail(self, **payload):
        """
            Gets the barcode of a product from request and
            returns that specific product's location and quantity.
        """
        _logger.info("/api/get_product_detail payload: %s", payload)

        try:

            payload_data = payload
            domain = []
            if 'last_sync_time' in payload_data and payload_data['last_sync_time']:
                domain += filter_by_last_sync_time('product.product', payload_data)

            # TODO
            res = self.get_product_detail_response_data(self, domain, payload_data)

            if res['status']:
                return valid_response(res['data'])
            else:
                return invalid_response(res['code'], res['message'], 200)

        except Exception as e:
            _logger.exception("Error while getting product details for payload: %s", payload)
            error_msg = 'Error while getting product details.'
            return invalid_response('bad_request', error_msg, 200)

    @staticmethod
    def get_batch_detail_response_data(self, stock_picking_batch_objs, response_data):
        for stock_picking_batch_obj in stock_picking_batch_objs:
            picking = []
            move = []
            move_line = []
            for picking_id in stock_picking_batch_obj.picking_ids:
                rfid = picking_id.rfid_tag.name if 'rfid_tag' in picking_id._fields else ""
                picking.append({
                    'id': picking_id.id,
                    'name': picking_id.name,
                    'rfid_tag': rfid or "",
                    'source_doc': picking_id.origin if picking_id.origin else "",
                    'schedule_date': picking_id.scheduled_date or "",
                    'deadline': picking_id.date_deadline or "",
                    'done_date': picking_id.date_done or "",
                    'partner_id': [str(picking_id.partner_id.id),
                                   picking_id.partner_id.name] if picking_id.partner_id else [],
                    'location_id': [str(picking_id.location_id.id),
                                    picking_id.location_id.display_name] if picking_id.location_id else [],
                    'location_dest_id': [str(picking_id.location_dest_id.id),
                                         picking_id.location_dest_id.display_name] if picking_id.location_dest_id else [],
                    'operation_type_id': [str(picking_id.picking_type_id.id),
                                          picking_id.picking_type_id.name] if picking_id.picking_type_id else [],
                    'priority': dict(picking_id._fields['priority'].selection).get(picking_id.priority),
                    'company': picking_id.company_id.name,
                    'sale_id': picking_id.sale_id.id if picking_id.sale_id else 0,
                    'purchase_id': picking_id.purchase_id.id if picking_id.purchase_id else 0,
                    'state': dict(picking_id._fields['state'].selection).get(picking_id.state),
                    'shipping_policy': picking_id.move_type,
                    'create_uid': [str(picking_id.create_uid.id),
                                   picking_id.create_uid.name] if picking_id.create_uid else [],
                    'create_date': picking_id.create_date,
                    'write_uid': [str(picking_id.write_uid.id),
                                  picking_id.write_uid.name] if picking_id.write_uid else [],
                    'write_date': picking_id.write_date,
                })

            for move_id in stock_picking_batch_obj.move_ids:
                move.append({
                    'id': move_id.id,
                    'picking_id': move_id.picking_id.id,
                    'product_id': move_id.product_id.id,
                    'product': move_id.product_id.display_name,
                    'product_packaging': [str(move_id.product_packaging_id.id),
                                          move_id.product_packaging_id.name] if move_id.product_packaging_id else [],
                    'product_code': move_id.product_id.default_code or "",
                    'description_picking': move_id.description_picking or "",
                    'product_uom_qty': move_id.product_uom_qty,
                    'state': dict(move_id._fields['state'].selection).get(move_id.state),
                })

            for line_id in stock_picking_batch_obj.move_line_ids:
                quant_line = []

                stock_quants = request.env['stock.quant'].search([
                    ('product_id', '=', line_id.product_id.id), ('quantity', '>=', 0)
                ])
                product_stock_quant_ids = stock_quants.filtered(
                    lambda q: q.company_id in request.env.companies and q.location_id.usage == 'internal'
                )

                for quant_id in product_stock_quant_ids:
                    rfid = quant_id.lot_id.rfid_tag.name if 'rfid_tag' in quant_id.lot_id._fields else ""
                    quant_line.append({
                        'id': quant_id.id,
                        'location': quant_id.location_id.complete_name,
                        'lot_serial': quant_id.lot_id.name if quant_id.lot_id else "",
                        'rfid_tag': rfid or "",
                        'on_hand_quantity': quant_id.quantity,
                    })
                move_line.append({
                    'id': line_id.id,
                    'picking_id': line_id.picking_id.id,
                    'picking_name': line_id.picking_id.name,
                    'product_id': line_id.product_id.id,
                    'product': line_id.product_id.name,
                    'product_packages': [str(line_id.result_package_id.id),
                                         line_id.result_package_id.name] if line_id.result_package_id else [],
                    'product_code': line_id.product_id.default_code or "",
                    'product_uom_qty': line_id.reserved_uom_qty,
                    'quantity_done': line_id.qty_done,
                    'quant_ids': quant_line,
                })

            response_data.append({
                'id': stock_picking_batch_obj.id,
                'name': stock_picking_batch_obj.name,
                'is_wave': stock_picking_batch_obj.is_wave,
                'schedule_date': stock_picking_batch_obj.scheduled_date or "",
                'company': stock_picking_batch_obj.company_id.name,
                'picking': picking,
                'move': move,
                'move_line': move_line,
                'state': dict(stock_picking_batch_obj._fields['state'].selection).get(
                    stock_picking_batch_obj.state),
                'create_uid': [str(stock_picking_batch_obj.create_uid.id),
                               stock_picking_batch_obj.create_uid.name] if stock_picking_batch_obj.create_uid else [],
                'create_date': stock_picking_batch_obj.create_date,
                'write_uid': [str(stock_picking_batch_obj.write_uid.id),
                              stock_picking_batch_obj.write_uid.name] if stock_picking_batch_obj.write_uid else [],
                'write_date': stock_picking_batch_obj.write_date,
            })
        return response_data

    @validate_token
    @http.route("/api/get_batch_detail", type="http", auth="none", methods=["GET"], csrf=False)
    def get_batch_detail(self, **payload):
        """
            Gets the name of a stock_picking_batch record from request and
            returns that specific stock_picking_batch record's details.
            If name of a stock_picking_batch not in request then returns
            all the stock_picking_batch record details of ready state.
        """

        _logger.info("/api/get_batch_picking_detail payload: %s", payload)

        try:
            response_data = []
            payload_data = payload
            stock_picking_batch_domain = []
            if 'last_sync_time' in payload_data and payload_data['last_sync_time']:
                stock_picking_batch_domain += filter_by_last_sync_time('stock.picking.batch', payload_data)
            stock_picking_batch = request.env['stock.picking.batch'].search(stock_picking_batch_domain)
            stock_picking_batch_objs = False

            user_id, is_admin = self._get_user_stock_group(self)

            if 'barcode' in payload_data or 'batch_id' in payload_data or \
                    'picking_type_id' in payload_data or 'is_wave' in payload_data:
                domain = [('state', '=', 'in_progress')]
                if 'barcode' in payload_data:
                    if payload_data['barcode']:
                        stock_picking_batch_domain = [('name', '=', payload_data.get('barcode'))]
                        if is_admin == 0:
                            stock_picking_batch_domain = stock_picking_batch_domain + [('user_id', '=', user_id.id)]
                        stock_picking_batch_objs = stock_picking_batch.sudo().search(stock_picking_batch_domain)
                elif 'batch_id' in payload_data:
                    if payload_data['batch_id']:
                        stock_picking_batch_domain = [
                            ('id', '=', int(payload_data['batch_id']))
                        ]
                        if is_admin == 0:
                            stock_picking_batch_domain = stock_picking_batch_domain + [('user_id', '=', user_id.id)]
                        stock_picking_batch_objs = stock_picking_batch.sudo().search(stock_picking_batch_domain)
                elif 'picking_type_id' in payload_data:
                    if payload_data['picking_type_id']:
                        domain += [('picking_type_id', '=', int(payload_data.get('picking_type_id')))]
                        if is_admin == 0:
                            domain += [('user_id', '=', user_id.id)]
                        stock_picking_batch_objs = stock_picking_batch.sudo().search(domain)
                elif 'is_wave' in payload_data:
                    if payload_data['is_wave']:
                        domain += [('is_wave', '=', int(payload_data.get('is_wave')))]
                        if is_admin == 0:
                            domain += [('user_id', '=', user_id.id)]
                        stock_picking_batch_objs = stock_picking_batch.sudo().search(domain)
            else:
                stock_picking_batch_domain = [('state', '=', 'in_progress'),
                                              ('company_id', '=', request.env.user.company_id.id)]
                if is_admin == 0:
                    stock_picking_batch_domain += [('user_id', '=', user_id.id)]
                if 'last_sync_time' in payload_data and payload_data['last_sync_time']:
                    stock_picking_batch_domain += filter_by_last_sync_time('stock.picking.batch', payload_data)
                stock_picking_batch_objs = stock_picking_batch.sudo().search(stock_picking_batch_domain)

            if stock_picking_batch_objs:
                if 'last_sync_time' in payload_data and payload_data['last_sync_time']:
                    stock_picking_batch_domain += filter_by_last_sync_time('stock.picking.batch', payload_data)
                stock_picking_batch_objs = stock_picking_batch_objs.search(stock_picking_batch_domain)

                response_data_list = self.get_batch_detail_response_data(self, stock_picking_batch_objs, response_data)
                return valid_response(response_data_list)
            else:
                return invalid_response('not_found', 'No Batch Picking record found.')
        except Exception as e:
            _logger.exception("Error while getting batch picking details for payload: %s", payload)
            error_msg = 'Error while getting batch picking details.'
            return invalid_response('bad_request', error_msg, 200)

    @staticmethod
    def get_location_detail_response_data(stock_location_objs):

        response_data = []
        for location in stock_location_objs:
            current_stock = []
            stock_quants = request.env['stock.quant'].search([
                ('location_id', 'child_of', location.id)
            ])
            if stock_quants:
                for quant_id in stock_quants:
                    current_stock.append({
                        'id': quant_id.id,
                        'product_id': quant_id.product_id.id,
                        'product': quant_id.product_id.name,
                        'product_code': quant_id.product_id.default_code or "",
                        'barcode': quant_id.product_id.barcode or "",
                        'location': quant_id.location_id.complete_name,
                        'lot_serial': quant_id.lot_id.name if quant_id.lot_id else "",
                        'on_hand_quantity': quant_id.quantity,
                    })
            response_data.append({
                'id': location.id,
                'location_name': location.name,
                'parent_location': location.location_id.complete_name or "",
                'location_type': location.usage,
                'company': location.company_id.name,
                'barcode': location.barcode or "",
                'storage_category': location.storage_category_id.name or "",
                'is_scrap_location': location.scrap_location,
                'is_return_location': location.return_location,
                'inventory_frequency': location.cyclic_inventory_frequency or 0,
                'last_inventory_date': location.last_inventory_date or "",
                'next_inventory_date': location.next_inventory_date or "",
                'removal_strategy': location.removal_strategy_id.name or "",
                'comment': location.comment or "",
                'current_stock': current_stock,
            })
        return response_data

    @validate_token
    @http.route("/api/get_location_detail", type="http", auth="none", methods=["GET"], csrf=False)
    def get_location_detail(self, **payload):
        """
            Gets the barcode of a location from request and
            returns that specific location's details.
        """
        _logger.info("/api/get_location_detail payload: %s", payload)

        try:
            payload_data = payload
            domain = []

            if 'last_sync_time' in payload_data and payload_data['last_sync_time']:
                domain += filter_by_last_sync_time('stock.location', payload_data)

            stock_location = request.env['stock.location'].search(domain)

            if 'barcode' in payload_data and payload_data['barcode']:
                # get stock.location object search by barcode
                stock_location_objs = stock_location.sudo().search([
                    ('barcode', '=', payload_data.get('barcode'))], limit=1)
            else:
                domain.append(('usage', 'in', ['internal']))
                domain.append(('company_id', '=', request.env.user.company_id.id))
                stock_location_objs = stock_location.sudo().search(domain)

            if stock_location_objs:
                response_data = self.get_location_detail_response_data(stock_location_objs)
                return valid_response(response_data)
            else:
                return invalid_response('not_found', 'No location found.')
        except Exception as e:
            _logger.exception("Error while getting location details for payload: %s", payload)
            error_msg = 'Error while getting location details.'
            return invalid_response('bad_request', error_msg, 200)

    @staticmethod
    def _generate_prod_wise_purchase_report(self, prod_id):
        try:
            response_data = []

            parameters = {
                "domain": [
                    "&",
                    "&",
                    [
                        "state",
                        "in",
                        [
                            "purchase",
                            "done"
                        ]
                    ],
                    [
                        "product_tmpl_id",
                        "in",
                        [
                            prod_id
                        ]
                    ],
                    [
                        "date_approve",
                        ">=",
                        "2021-07-28"
                    ]
                ],
                "groupby": [
                    "date_approve:day"
                ],
                "fields": [
                    "__count",
                    "qty_ordered:sum"
                ],
                "context": {
                    "lang": "en_US",
                    "tz": "Asia/Dhaka",
                    "uid": 2,
                    "allowed_company_ids": [
                        1
                    ],
                    "fill_temporal": True,
                    "active_model": "product.template",
                    "active_id": prod_id,
                    "active_ids": [
                        prod_id
                    ],
                    "graph_measure": "qty_ordered"
                },
                "lazy": False
            }
            response_data = request.env['purchase.report'].with_context(parameters['context']).sudo().web_read_group(
                domain=parameters['domain'], groupby=parameters['groupby'],
                fields=parameters['fields'], lazy=parameters['lazy'])
            for data in response_data['groups']:
                if data.get('__domain', False):
                    data.pop('__domain', None)
                if data.get('__range', False):
                    data.pop('__range', None)
                if not data['qty_ordered']:
                    data['qty_ordered'] = 0

            read_group_params = {
                "domain": [
                    "&",
                    "&",
                    [
                        "state",
                        "in",
                        [
                            "purchase",
                            "done"
                        ]
                    ],
                    [
                        "product_tmpl_id",
                        "in",
                        [
                            prod_id
                        ]
                    ],
                    [
                        "date_approve",
                        ">=",
                        "2021-07-29"
                    ]
                ],
                "groupby": [],
                "fields": [
                    "__count",
                    "order_id:count_distinct",
                    "untaxed_total:sum",
                    "price_total:sum",
                    "price_subtotal_confirmed_orders:sum(price_total)",
                    "price_subtotal_all_orders:sum(untaxed_total)",
                    "purchase_orders:count_distinct(order_id)",
                    "avg_receipt_delay:avg(avg_receipt_delay)",
                    "avg_days_to_purchase:avg(avg_days_to_purchase)"
                ],
                "context": {
                    "lang": "en_US",
                    "tz": "Asia/Dhaka",
                    "uid": 2,
                    "allowed_company_ids": [
                        1
                    ],
                    "active_model": "product.template",
                    "active_id": prod_id,
                    "active_ids": [
                        prod_id
                    ],
                    "graph_measure": "qty_ordered"
                },
                "lazy": False
            }
            read_group_res_data = request.env['purchase.report'].with_context(
                read_group_params['context']).sudo().read_group(
                domain=read_group_params['domain'], groupby=read_group_params['groupby'],
                fields=read_group_params['fields'], lazy=read_group_params['lazy'])
            for elem in read_group_res_data:
                for key in elem:
                    if not elem[key]:
                        elem[key] = 0
            response_data['total_count'] = read_group_res_data

            return valid_response(response_data)
        except Exception as e:
            _logger.exception("Error while generating purchase report for prod_id: %s", prod_id)
            return invalid_response('bad_request', 'Error while generating purchase report.', 200)

    @validate_token
    @http.route("/api/get_purchase_report", type="http", auth="none", methods=["GET"], csrf=False)
    def get_purchase_report(self, **payload):
        """
            Gets the name of a stock_picking_batch record from request and
            returns that specific stock_picking_batch record's details.
            If name of a stock_picking_batch not in request then returns
            all the stock_picking_batch record details of ready state.
        """

        _logger.info("/api/get_purchase_report payload: %s", payload)
        payload_data = payload

        if 'product_tmpl_id' in payload_data:
            return self._generate_prod_wise_purchase_report(self, prod_id=int(payload_data['product_tmpl_id']))
        else:
            product_template_obj = request.env['product.template'].search([])

    @validate_token
    @http.route("/api/sync_barcode_data", type="http", auth="none", methods=["GET"], csrf=False)
    def sync_barcode_data(self, **payload):
        """
            Returns product, picking, batch/wave, location barcode and route.
        """

        _logger.info("/api/sync_barcode_data GET payload: %s", payload)
        try:
            response_data = []
            user_id, is_admin = self._get_user_stock_group(self)
            warehouse_id = user_id.warehouse_id

            product_product_objs = request.env['product.product'].search(
                [('active', '=', True), ('barcode', '!=', False)])
            if product_product_objs:
                for product in product_product_objs:
                    response_data.append({
                        "barcode": product.barcode,
                        "route": "product"
                    })
            stock_picking_domain = [('state', '=', 'assigned'), ('company_id', '=', request.env.user.company_id.id)]
            if is_admin == 0:
                stock_picking_domain = stock_picking_domain + [('user_id', '=', user_id.id)]
            stock_picking_objs = request.env['stock.picking'].search(stock_picking_domain)

            if stock_picking_objs:
                for picking in stock_picking_objs:
                    response_data.append({
                        "barcode": picking.name,
                        "route": "picking"
                    })
            stock_picking_batch_domain = [('state', '=', 'in_progress'),
                                          ('company_id', '=', request.env.user.company_id.id)]
            if is_admin == 0:
                stock_picking_batch_domain = stock_picking_batch_domain + [('user_id', '=', user_id.id)]
            stock_picking_batch_objs = request.env['stock.picking.batch'].search(stock_picking_batch_domain)
            if stock_picking_batch_objs:
                for batch in stock_picking_batch_objs:
                    response_data.append({
                        "barcode": batch.name,
                        "route": "batch_wave"
                    })
            stock_location_objs = request.env['stock.location'].sudo().search(
                [('usage', 'in', ['internal']), ('barcode', '!=', False),
                 ('company_id', '=', request.env.user.company_id.id)])
            if stock_location_objs:
                for location in stock_location_objs:
                    response_data.append({
                        "barcode": location.barcode,
                        "route": "location"
                    })
            product_package_type_objs = request.env['stock.package.type'].sudo().search([])
            if product_package_type_objs:
                for package_type in product_package_type_objs:
                    if package_type.barcode:
                        response_data.append({
                            "barcode": package_type.barcode,
                            "route": "product_package_type"
                        })
            product_packaging_objs = request.env['product.packaging'].sudo().search([])
            if product_packaging_objs:
                for packaging in product_packaging_objs:
                    if packaging.barcode:
                        response_data.append({
                            "barcode": packaging.barcode,
                            "route": "product_packaging"
                        })
            product_packages_domain = [('location_id.usage', '!=', 'customer')]
            if is_admin == 0:
                product_packages_domain = product_packages_domain + \
                                          [('location_id.warehouse_id', '=', warehouse_id.id)]
            product_packages_objs = request.env['stock.quant.package'].sudo().search(
                product_packages_domain)
            if product_packages_objs:
                for package in product_packages_objs:
                    if package.name:
                        response_data.append({
                            "barcode": package.name,
                            "route": "product_packages"
                        })
            if response_data:
                return valid_response(response_data)
            else:
                return invalid_response('not_found', 'No Data Found.')
        except Exception as e:
            _logger.exception("Error while syncing barcode data")
            error_msg = 'Error while syncing barcode data.'
            return invalid_response('bad_request', error_msg, 200)

    @staticmethod
    def _get_product_package_type(self, payload_data):

        response_data = []
        package_carrier_value = str()
        package_carrier_key = str()
        product_package_type = request.env['stock.package.type']
        product_package_type_objs = False

        if 'id' in payload_data or 'barcode' in payload_data:
            if 'id' in payload_data:
                if payload_data['id']:
                    product_package_type_objs = product_package_type.sudo().search(
                        [('id', '=', payload_data.get('id'))], limit=1)
            elif 'barcode' in payload_data:
                if payload_data['barcode']:
                    product_package_type_objs = product_package_type.sudo().search(
                        [('barcode', '=', payload_data.get('barcode'))], limit=1)
        else:
            product_package_type_objs = product_package_type.sudo().search([])

        if product_package_type_objs:
            for package_type in product_package_type_objs:
                storage_category_capacity = []
                for category_capacity in package_type.storage_category_capacity_ids:
                    storage_category_capacity.append(
                        {
                            'storage_category_id': [str(category_capacity.storage_category_id.id),
                                                    category_capacity.storage_category_id.name] if category_capacity.storage_category_id else [],
                            'product_id': [str(category_capacity.product_id.id),
                                           category_capacity.product_id.display_name] if category_capacity.product_id else [],
                            'package_type_id': [str(category_capacity.package_type_id.id),
                                                category_capacity.package_type_id.name] if category_capacity.package_type_id else [],
                            'product_uom_id': [str(category_capacity.product_uom_id.id),
                                               category_capacity.product_uom_id.name] if category_capacity.product_uom_id else [],
                            'quantity': category_capacity.quantity or "",
                        })
                if 'package_carrier_type' in package_type._fields:
                    package_carrier_value = dict(package_type._fields['package_carrier_type'].selection).get(
                        package_type.package_carrier_type)
                    package_carrier_key = package_type.package_carrier_type
                response_data.append(
                    {
                        'id': package_type.id,
                        'barcode': package_type.barcode or "",
                        'name': package_type.name,
                        'display_name': package_type.display_name,
                        'packaging_length': package_type.packaging_length,
                        'width': package_type.width,
                        'height': package_type.height,
                        'length_uom_name': package_type.length_uom_name or "",
                        'base_weight': package_type.base_weight,
                        'max_weight': package_type.max_weight,
                        'weight_uom_name': package_type.weight_uom_name or "",
                        'package_carrier_type': [package_carrier_key,
                                                 package_carrier_value] if package_carrier_value else "",
                        'shipper_package_code': package_type.shipper_package_code or "" if 'shipper_package_code' in package_type._fields else "",
                        'sequence': package_type.sequence,
                        'company_id': [str(package_type.company_id.id),
                                       package_type.company_id.name] if package_type.company_id else [],
                        'storage_category_capacity_ids': storage_category_capacity,
                        'create_uid': [str(package_type.create_uid.id),
                                       package_type.create_uid.name] if package_type.create_uid else [],
                        'create_date': package_type.create_date.strftime(DEFAULT_SERVER_DATETIME_FORMAT),
                        'write_uid': [str(package_type.write_uid.id),
                                      package_type.write_uid.name] if package_type.write_uid else [],
                        'write_date': package_type.write_date.strftime(DEFAULT_SERVER_DATETIME_FORMAT),
                    })
            return response_data
        else:
            return {"status": False, "response": 'not_found', "message": 'No product package type found.'}

    @validate_token
    @http.route("/api/get_product_package_type", type="http", auth="none", methods=["GET"], csrf=False)
    def get_product_package_type(self, **payload):
        """
            Returns product_package_type info.
        """

        _logger.info("/api/get_product_package_type GET payload: %s", payload)
        try:
            payload_data = payload
            packages_enabled = request.env.user.has_group('stock.group_tracking_lot')
            if packages_enabled:
                response_data = self._get_product_package_type(self, payload_data)
                if isinstance(response_data, list):
                    return valid_response(response_data)
                elif isinstance(response_data, dict):
                    if not response_data['status']:
                        return invalid_response(response_data['response'], response_data['message'])
            else:
                return invalid_response('not_enabled', 'Package is not enabled in settings.')

        except Exception as e:
            _logger.exception("Error while getting product package type data")
            error_msg = 'Error while getting product package type data.'
            return invalid_response('bad_request', error_msg, 200)

    @staticmethod
    def _get_product_packages(self, payload_data):
        response_data = []
        user_id, is_admin = self._get_user_stock_group(self)
        stock_quant_package = request.env['stock.quant.package']
        stock_picking = request.env['stock.picking']
        warehouse_id = user_id.warehouse_id
        stock_quant_package_objs = False
        if 'id' in payload_data or 'package' in payload_data:
            if 'id' in payload_data:
                if payload_data['id']:
                    stock_quant_packages_domain = [('id', '=', int(payload_data['id']))]
                    if is_admin == 0:
                        stock_quant_packages_domain = stock_quant_packages_domain + [
                            ('location_id.warehouse_id', '=', warehouse_id.id)]
                    stock_quant_package_objs = stock_quant_package.sudo().search(stock_quant_packages_domain, limit=1)
            elif 'package' in payload_data:
                if payload_data['package']:
                    stock_quant_packages_domain = [('display_name', '=', payload_data.get('package'))]
                    if is_admin == 0:
                        stock_quant_packages_domain = stock_quant_packages_domain + [
                            ('location_id.warehouse_id', '=', warehouse_id.id)]
                    stock_quant_package_objs = stock_quant_package.sudo().search(stock_quant_packages_domain, limit=1)
        else:
            stock_quant_packages_domain = []
            if is_admin == 0:
                stock_quant_packages_domain.append(('location_id.warehouse_id.id', '=', warehouse_id.id))
            stock_quant_package_objs = stock_quant_package.sudo().search(stock_quant_packages_domain)
        if stock_quant_package_objs:
            for package in stock_quant_package_objs:
                package_content = []
                stock_picking_data = []
                transfer_values = package.action_view_picking()
                stock_picking_objs = stock_picking.sudo().search(transfer_values['domain'], order='id')
                for stock_picking in stock_picking_objs:
                    stock_picking_data.append(
                        {
                            'id': stock_picking.id,
                            'name': stock_picking.name
                        })
                for quant in package.quant_ids:
                    package_content.append(
                        {
                            'product_id': [str(quant.product_id.id),
                                           quant.product_id.display_name] if quant.product_id else [],
                            'lot_id': [str(quant.lot_id.id),
                                       quant.lot_id.name] if quant.lot_id else [],
                            'product_uom_id': [str(quant.product_uom_id.id),
                                               quant.product_uom_id.name] if quant.product_uom_id else [],
                            'quantity': quant.quantity or "",
                        })
                package_use_key = package.package_use
                package_use_value = dict(package._fields['package_use'].selection).get(package.package_use)
                response_data.append(
                    {
                        'id': package.id,
                        'name': package.name,
                        'display_name': package.display_name,
                        'corresponding_transfer': stock_picking_data,
                        'package_type_id': [str(package.package_type_id.id),
                                            package.package_type_id.name] if package.package_type_id else [],
                        'pack_date': package.pack_date.strftime(DEFAULT_SERVER_DATETIME_FORMAT),
                        'company_id': [str(package.company_id.id),
                                       package.company_id.name] if package.company_id else [],
                        'owner_id': [str(package.owner_id.id),
                                     package.owner_id.name] if package.owner_id else [],
                        'location_id': [str(package.location_id.id),
                                        package.location_id.complete_name] if package.location_id else [],
                        'warehouse_id': [str(package.location_id.warehouse_id.id),
                                         package.location_id.warehouse_id.name] if package.location_id.warehouse_id else [],
                        'package_use': [package_use_key, package_use_value] if package_use_value else "",
                        'shipping_weight': package.shipping_weight,
                        'valid_sscc': package.valid_sscc,
                        'weight': round(package.weight, 2) if package.weight else package.weight,
                        'weight_is_kg': package.weight_is_kg,
                        'weight_uom_name': package.weight_uom_name or "",
                        'weight_uom_rounding': package.weight_uom_rounding,
                        'quant_ids': package_content,
                        'create_uid': [str(package.create_uid.id),
                                       package.create_uid.name] if package.create_uid else [],
                        'create_date': package.create_date.strftime(DEFAULT_SERVER_DATETIME_FORMAT),
                        'write_uid': [str(package.write_uid.id),
                                      package.write_uid.name] if package.write_uid else [],
                        'write_date': package.write_date.strftime(DEFAULT_SERVER_DATETIME_FORMAT),
                    })
            return response_data
        else:
            return {"status": False, "response": 'not_found', "message": 'No product package type found.'}

    @validate_token
    @http.route("/api/get_product_packages", type="http", auth="none", methods=["GET"], csrf=False)
    def get_product_packages(self, **payload):
        """
            Returns product_package_type info.
        """

        _logger.info("/api/get_product_packages GET payload: %s", payload)
        try:
            payload_data = payload
            packages_enabled = request.env.user.has_group('stock.group_tracking_lot')
            if packages_enabled:
                response_data = self._get_product_packages(self, payload_data)
                if isinstance(response_data, list):
                    return valid_response(response_data)
                elif isinstance(response_data, dict):
                    if not response_data['status']:
                        return invalid_response(response_data['response'], response_data['message'])
            else:
                return invalid_response('not_enabled', 'Package is not enabled in settings.')

        except Exception as e:
            _logger.exception("Error while getting product package data")
            error_msg = 'Error while getting product package data.'
            return invalid_response('bad_request', error_msg, 200)

    @staticmethod
    def _get_package_sequence(self, payload_data):

        response_data = []
        number_next_actual = str()
        package_sequence_objs = False
        sequences = request.env['ir.sequence']
        stock_quant_package_obj = request.env['stock.quant.package']

        if 'id' in payload_data or 'sequence_code' in payload_data:
            if 'id' in payload_data:
                if payload_data['id']:
                    package_sequence_domain = [
                        ('id', '=', int(payload_data['id']))]
                    package_sequence_objs = sequences.sudo().search(package_sequence_domain, limit=1)
                elif 'sequence_code' in payload_data:
                    if payload_data['sequence_code']:
                        package_sequence_domain = [
                            ('code', '=', int(payload_data['sequence_code']))]
                        package_sequence_objs = sequences.sudo().search(package_sequence_domain, limit=1)
        else:
            package_sequence_domain = [('name', '=', 'Packages')]
            package_sequence_objs = sequences.sudo().search(package_sequence_domain)

        if package_sequence_objs:
            for sequence in package_sequence_objs:
                # stock_quant_package = stock_quant_package_obj.search(
                #     [('name', 'ilike', sequence.prefix)], order='id desc', limit=1)
                # if stock_quant_package:
                #     print('ok-------------',stock_quant_package.name,sequence.prefix)
                #     number_next_actual = int(
                #         ''.join(filter(str.isdigit, stock_quant_package.name)))
                implementation_key = sequence.implementation
                implementation_value = dict(
                    sequence._fields['implementation'].selection).get(sequence.implementation)
                response_data.append({
                    'name': sequence.name,
                    'code': sequence.code or "",
                    'active': sequence.active,
                    'implementation': [implementation_key, implementation_value] if implementation_value else "",
                    'prefix': sequence.prefix or "",
                    'suffix': sequence.suffix or "",
                    'sequence_size': sequence.padding,
                    'number_increment': sequence.number_increment,
                    'number_next': sequence.number_next,
                    'number_next_actual': sequence.number_next_actual,
                    'is_mobile_app': sequence.is_mobile_app
                })

            return response_data
        return {"status": False, "response": 'not_found', "message": 'No package sequence found.'}

    @validate_token
    @http.route("/api/get_package_sequence", type="http", auth="none", methods=["GET"], csrf=False)
    def get_package_sequence(self, **payload):
        """
            Returns package sequence info.
        """

        _logger.info("/api/get_package_sequence GET payload: %s", payload)
        try:
            payload_data = payload
            packages_enabled = request.env.user.has_group('stock.group_tracking_lot')
            if packages_enabled:
                response_data = self._get_package_sequence(self, payload_data)
                if isinstance(response_data, list):
                    return valid_response(response_data)
                elif isinstance(response_data, dict):
                    if not response_data['status']:
                        return invalid_response(response_data['response'], response_data['message'])
            else:
                return invalid_response('not_enabled', 'Package is not enabled in settings.')

        except Exception as e:
            _logger.exception("Error while getting package sequence data")
            error_msg = 'Error while getting package sequence data.'
            return invalid_response('bad_request', error_msg, 200)

    @staticmethod
    def get_packaging_type_detail_response_data(self, payload_data):

        response_data = []
        product_packaging = request.env['product.packaging']
        product_packaging_objs = False

        if 'barcode' in payload_data:
            if payload_data['barcode']:
                product_packaging_domain = [('barcode', '=', payload_data.get('barcode'))]
                product_packaging_objs = product_packaging.sudo().search(product_packaging_domain, limit=1)
        elif 'name' in payload_data:
            if payload_data['name']:
                product_packaging_domain = [('name', '=', payload_data.get('name'))]
                product_packaging_objs = product_packaging.sudo().search(product_packaging_domain, limit=1)
        else:
            product_packaging_objs = product_packaging.sudo().search([])
        if product_packaging_objs:
            for product_package in product_packaging_objs:
                response_data.append({
                    'id': str(product_package.id),
                    'name': product_package.name,
                    'barcode': product_package.barcode or "",
                    'company_id': [str(product_package.company_id.id),
                                   product_package.company_id.name] if product_package.company_id else [],
                    'display_name': product_package.display_name,
                    'package_type_id': [str(product_package.package_type_id.id),
                                        product_package.package_type_id.name] if product_package.package_type_id else [],
                    'product_id': [str(product_package.product_id.id),
                                   product_package.product_id.name] if product_package.product_id else [],
                    'product_uom_id': [str(product_package.product_uom_id.id),
                                       product_package.product_uom_id.name] if product_package.product_uom_id else [],
                    'purchase': product_package.purchase,
                    'qty': str(product_package.qty or ""),
                    'route_ids': [str(product_package.route_ids.id),
                                  product_package.route_ids.name] if product_package.route_ids else [],
                    'sales': product_package.sales,
                    'sequence': str(product_package.sequence or ""),
                    'create_date': product_package.create_date,
                    'create_uid': [str(product_package.create_uid.id),
                                   product_package.create_uid.name] if product_package.create_uid else [],
                    'write_date': product_package.write_date,
                    'write_uid ': [str(product_package.write_uid.id),
                                   product_package.write_uid.name] if product_package.write_uid else [],
                })
            return response_data
        else:
            return {"status": False, "response": 'not_found', "message": 'No packaging details found.'}

    @validate_token
    @http.route("/api/get_packaging_type_detail", type="http", auth="none", methods=["GET"], csrf=False)
    def get_packaging_type_detail(self, **payload):
        """
            Gets name or barcode from the request and return packaging type information.
        """
        _logger.info("/api/get_packaging_detail payload: %s", payload)
        response_data = []
        payload_data = payload
        user_id, is_admin = self._get_user_stock_group(self)
        packaging_enabled = user_id.has_group('product.group_stock_packaging')
        try:
            if packaging_enabled:
                response_data = self.get_packaging_type_detail_response_data(self, payload_data)
                if isinstance(response_data, list):
                    return valid_response(response_data)
                elif isinstance(response_data, dict):
                    if not response_data['status']:
                        return invalid_response(response_data['response'], response_data['message'])
            else:
                error_msg = 'Product Packaging is not enabled in settings.'
                return invalid_response("not_enabled", error_msg, 200)
        except Exception as e:
            _logger.exception("Error while processing response data")
            error_msg = 'Error while generating packaging type data.'
            return invalid_response('bad_request', error_msg, 200)

    @staticmethod
    def _get_stock_quants(self, payload_data):
        response_data = []
        stock_quant_domain = [('location_id.usage', 'in', ['internal', 'transit'])]
        stock_quant_objs = False
        stock_quant = request.env['stock.quant']
        user_id, is_admin = self._get_user_stock_group(self)
        warehouse_id = user_id.warehouse_id

        if 'location_barcode' in payload_data or 'product_id' in payload_data:
            if 'location_barcode' in payload_data:
                if payload_data['location_barcode']:
                    stock_quant_domain = stock_quant_domain + \
                                         [('location_id.barcode', '=', payload_data['location_barcode'])]
                    if is_admin == 0:
                        stock_quant_domain = stock_quant_domain + \
                                             [('warehouse_id', '=', warehouse_id.id)]
                    stock_quant_objs = stock_quant.with_context(inventory_mode=True).search(
                        stock_quant_domain, order="location_id")
            elif 'product_id' in payload_data:
                if payload_data['product_id']:
                    stock_quant_domain = stock_quant_domain + \
                                         [('product_id', '=', int(payload_data['product_id']))]
                    if is_admin == 0:
                        stock_quant_domain = stock_quant_domain + \
                                             [('warehouse_id', '=', warehouse_id.id)]
                    stock_quant_objs = stock_quant.with_context(inventory_mode=True).search(
                        stock_quant_domain, order="location_id")
        else:
            if is_admin == 0:
                stock_quant_domain = stock_quant_domain + \
                                     [('warehouse_id', '=', warehouse_id.id)]
            stock_quant_objs = stock_quant.with_context(inventory_mode=True).search(
                stock_quant_domain, order="location_id")
        if stock_quant_objs:
            for quant_id in stock_quant_objs:
                response_data.append({
                    'location_barcode': quant_id.location_id.barcode or "",
                    'product_id': [str(quant_id.product_id.id),
                                   quant_id.product_id.display_name] if quant_id.product_id else [],
                    'lot_id': [str(quant_id.lot_id.id),
                               quant_id.lot_id.name] if quant_id.lot_id else [],
                    'package_id': [str(quant_id.package_id.id),
                                   quant_id.package_id.name] if quant_id.package_id else [],
                    'owner_id': [str(quant_id.owner_id.id),
                                 quant_id.owner_id.name] if quant_id.owner_id else [],
                    'location_id': [str(quant_id.location_id.id),
                                    quant_id.location_id.display_name] if quant_id.location_id else [],
                    'quantity': quant_id.quantity,
                    'product_uom_id': [str(quant_id.product_uom_id.id),
                                       quant_id.product_uom_id.name] if quant_id.product_uom_id else [],
                    'inventory_quantity': quant_id.inventory_quantity,
                    'inventory_diff_quantity': quant_id.inventory_diff_quantity,
                    'inventory_date': quant_id.inventory_date,
                    'user_id': [str(quant_id.user_id.id),
                                quant_id.user_id.name] if quant_id.user_id else [],
                })
            return response_data
        else:
            return {"status": False, "response": 'not_found', "message": 'No stock quant data found.'}

    @validate_token
    @http.route("/api/get_stock_quants", type="http", auth="none", methods=["GET"], csrf=False)
    def get_stock_quants(self, **payload):
        """
            Returns stock quant info.
        """
        _logger.info("/api/get_stock_quants GET payload: %s", payload)
        try:
            payload_data = payload
            response_data = self._get_stock_quants(self, payload_data)
            if isinstance(response_data, list):
                return valid_response(response_data)
            elif isinstance(response_data, dict):
                return invalid_response(response_data['response'], response_data['message'])
        except Exception as e:
            _logger.exception("Error while getting stock quant data")
            error_msg = 'Error while getting stock quant data.'
            return invalid_response('bad_request', error_msg, 200)
        
    @staticmethod
    def _get_res_partner(self, partner_objs, payload_data):
        response_data = []   
        if partner_objs:
            for contact in partner_objs:
                response_data.append({
                    'id':contact.id,
                    'name':contact.name,
                    'display_name':contact.display_name,
                    'email':contact.email or "",
                    'mobile':contact.mobile or "",
                    'phone':contact.phone or "",
                    'street':contact.street or "",
                    'street2':contact.street2 or "",
                    'city':contact.city or "",
                    'vat':contact.vat or "",
                    'state_id':[str(contact.state_id.id),
                               contact.state_id.name] if contact.state_id else [],
                    'country_id':[str(contact.country_id.id),
                               contact.country_id.name] if contact.country_id else [],
                    'zip':contact.zip or "",
                    'company_id':[str(contact.company_id.id),
                               contact.company_id.name] if contact.company_id else [],
                    'property_account_payable_id':[str(contact.property_account_payable_id.id),
                                                  contact.property_account_payable_id.name] if contact.property_account_payable_id else [],
                    'property_account_receivable_id':[str(contact.property_account_receivable_id.id),
                                                  contact.property_account_receivable_id.name] if contact.property_account_receivable_id else []
                })
            return response_data
        else:
            return {"status": False, "response": 'not_found', "message": 'No partner data found.'}       
        
    @validate_token
    @http.route("/api/get_res_partner_info", type="http", auth="none", methods=["GET"], csrf=False)
    def get_res_partner_info(self, **payload):
        """
            Returns res partner data.
        """
        _logger.info("/api/get_res_partner_info GET payload: %s", payload)
        try:
            payload_data = payload
            response_data = []
            partner_domain = []
            partner_objs = False
            partner = request.env['res.partner']
            user_id, is_admin = self._get_user_stock_group(self)
            if 'partner_id' in payload_data:
                if payload_data['partner_id']:
                    partner_domain.append(('id','=',int(payload_data['partner_id'])))
                    partner_objs = partner.search(partner_domain, limit = 1)       
            else:
                partner_objs = partner.search(partner_domain)
            response_data = self._get_res_partner(self, partner_objs, payload_data)
            if isinstance(response_data, list):
                return valid_response(response_data)
            elif isinstance(response_data, dict):
                return invalid_response(response_data['response'], response_data['message'])
        except Exception as e:
            _logger.exception("Error while getting res partner data")
            error_msg = 'Error while getting res partner data.'
            return invalid_response('bad_request', error_msg, 200)    
        
    

    # @staticmethod
    # def _get_inventory_history(self, payload_data):
    #     response_data = []
    #     move_line_objs = False
    #     stock_quant = request.env['stock.quant']
    #     stock_move_line = request.env['stock.move.line']
    #     user_id, is_admin = self._get_user_stock_group(self)
    #     warehouse_id = user_id.warehouse_id
    #     stock_quant_domain = [('is_inventory', '=', True), ('state', '=', 'done')]

    #     if 'location_id' in payload_data:
    #         if payload_data['location_id']:
    #             if is_admin == 0:
    #                 stock_quant_domain = stock_quant_domain + \
    #                     [('warehouse_id', '=', warehouse_id.id)]
    #             stock_quant_domain = stock_quant_domain + ['|', ('location_id', '=', int(
    #                 payload_data['location_id'])), ('location_dest_id', '=', int(payload_data['location_id']))]
    #             move_line_objs = stock_move_line.with_context(inventory_mode =True).search(
    #                 stock_quant_domain, order="location_id")
    #     else:
    #         return {"status": False, "response": 'not_found', "message": 'No location_id given.Please provide location_id.'}
    #         # stock_quant_domain = stock_quant_domain + [('location_id.usage', 'in', ['internal', 'transit'])]
    #         # move_line_objs = stock_move_line.with_context(inventory_mode =True).search(
    #         #         stock_quant_domain, order="location_id")

    #     if move_line_objs:
    #         for move_line in move_line_objs:
    #             response_data.append({
    #                 'id':move_line.id,
    #                 'date': move_line.date,
    #                 'reference': move_line.reference,
    #                 'product_id': [str(move_line.product_id.id),
    #                                 move_line.product_id.display_name] if move_line.product_id else [],
    #                 'lot_id': [str(move_line.lot_id.id),
    #                             move_line.lot_id.name] if move_line.lot_id else [],
    #                 'location_id': [str(move_line.location_id.id),
    #                                 move_line.location_id.display_name] if move_line.location_id else [],
    #                 'location_dest_id': [str(move_line.location_dest_id.id),
    #                                         move_line.location_dest_id.display_name] if move_line.location_dest_id else [],
    #                 'package_id':[str(move_line.package_id.id),
    #                                 move_line.package_id.name] if move_line.package_id else [],
    #                 'result_package_id':[str(move_line.result_package_id.id),
    #                                 move_line.result_package_id.name] if move_line.result_package_id else [],
    #                 'qty_done': move_line.qty_done,
    #                 'product_uom_id': [str(move_line.product_uom_id.id),
    #                                    move_line.product_uom_id.name] if move_line.product_uom_id else [],
    #                 'state': move_line.state
    #             })
    #         return response_data
    #     else:
    #         return {"status": False, "response": 'not_found', "message": 'No stock quant data found.'}

    # @validate_token
    # @http.route("/api/get_inventory_history", type="http", auth="none", methods=["GET"], csrf=False)
    # def get_inventory_history(self, **payload):
    #     """
    #         Returns stock quant info.
    #     """
    #     _logger.info("/api/get_inventory_history GET payload: %s", payload)
    #     try:
    #         payload_data = payload
    #         response_data = self._get_inventory_history(self, payload_data)
    #         if isinstance(response_data, list):
    #             return valid_response(response_data)
    #         elif isinstance(response_data, dict):
    #             return invalid_response(response_data['response'], response_data['message'])
    #     except Exception as e:
    #         _logger.exception("Error while getting inventory history data")
    #         error_msg = 'Error while getting inventory history data.'
    #         return invalid_response('bad_request', error_msg, 200)

    #######################################
    # POST APIs
    #######################################

    @staticmethod
    def post_picking_validate_response_data(payload):

        package_id = False
        package_obj = False
        params = ["picking_id", "move_line_ids"]
        stock_quant_package = request.env['stock.quant.package']

        req_data = payload if len(payload) > 0 else json.loads(
            request.httprequest.data.decode())  # convert the bytes format to dict format
        req_params = {key: req_data.get(key) for key in params if req_data.get(key)}
        picking_id, move_line_ids = (
            req_params.get("picking_id"),
            req_params.get("move_line_ids")
        )
        _data_included_in_body = all([picking_id, move_line_ids])
        if not _data_included_in_body:
            # ToDo: Check if it is a batch sync, change response.
            if 'batch_validate' in req_data:
                return {'code': "post_data_error", 'message': "Data is not valid, please check again",
                        'picking_id': req_data['picking_id'], "batch_validate": True}
            return {"status": False, 'code': "post_data_error", 'message': "Data is not valid, please check again",
                    'picking_id': req_data['picking_id']}
            # return invalid_response("post_data_error", "Data is not valid, please check again", 200)
        else:
            _logger.info("Updating Stock Picking Transfers")
            stock_picking = request.env['stock.picking']
            stock_move = request.env['stock.move']
            stock_move_line = request.env['stock.move.line']
            stock_prod_lot = request.env['stock.lot']

            stock_picking_obj = stock_picking.sudo().search([('id', '=', req_params.get("picking_id"))])

            if stock_picking_obj.state == 'done':
                # ToDo: Check if it is a batch sync, change response.
                if 'batch_validate' in req_data:
                    return {'code': "already_validated", 'message': "This picking is already done.",
                            'picking_id': stock_picking_obj.id, "batch_validate": True}
                return {"status": False, 'code': "already_validated", 'message': "This picking is already done.",
                        'picking_id': stock_picking_obj.id}
                # return invalid_response("already_validated", "This picking is already done.", 200)

            # if stock_picking_obj.picking_type_id.code == 'incoming':  # for Receipts
            #     stock_picking_obj.move_line_ids.unlink()

            if move_line_ids:
                for move_line in move_line_ids:

                    lot_detail = stock_prod_lot.sudo().search([
                        ('name', '=', move_line.get('lot_id')),
                        ('product_id', '=', move_line.get('product_id')),
                        ('company_id', '=', request.env.user.company_id.id)
                    ], limit=1)

                    lot_id = False
                    lot_name = False

                    if not lot_detail:
                        lot_detail = stock_prod_lot.create({
                            'name': move_line.get('lot_id'),
                            'product_id': move_line.get('product_id'),
                            'company_id': request.env.user.company_id.id,
                        })

                    if stock_picking_obj.picking_type_id.code in ['outgoing', 'internal']:
                        # for Delivery Orders and Internal transfer
                        lot_id = lot_detail.id
                    if stock_picking_obj.picking_type_id.code == 'incoming':  # for Receipts
                        if stock_picking_obj.picking_type_id.use_existing_lots:  # Use Existing lots enabled
                            lot_id = lot_detail.id
                        else:  # Use Create New lots enabled
                            lot_name = move_line.get('lot_id')

                    if move_line.get("id"):  # if move.line id exists in the system.
                        move_line_obj = stock_move_line.sudo().browse(move_line.get("id"))

                        move_line_obj.reserved_uom_qty = 0
                        move_line_obj.qty_done = move_line.get('quantity_done')
                        move_line_obj.lot_id = lot_id
                        move_line_obj.lot_name = lot_name

                        if move_line.get('product_package'):
                            package_obj = stock_quant_package.search(
                                [('name', '=', move_line.get('product_package'))], limit=1)
                            if not package_obj:
                                package_obj = stock_quant_package.create(
                                    {
                                        'name': move_line.get('product_package'),
                                        'package_use': 'disposable'
                                    })
                            move_line_obj.result_package_id = package_obj.id
                        elif isinstance(move_line.get('product_packages_id'), int):
                            move_line_obj.result_package_id = move_line.get('product_packages_id')
                            # package_obj = stock_quant_package.search(
                            #     [('name', '=', move_line.get('product_packages_id'))], limit=1)
                            # if not package_obj:

                        # if stock_picking_obj.picking_type_id.code == 'outgoing':  # for Delivery Orders
                        #     move_line_obj.lot_id = lot_detail[0].id
                        # if stock_picking_obj.picking_type_id.code == 'incoming':  # for Receipts
                        #     if stock_picking_obj.picking_type_id.use_existing_lots:  # Use Existing lots enabled
                        #         move_line_obj.lot_id = lot_detail[0].id
                        #     else:  # Use Create New lots enabled
                        #         move_line_obj.lot_name = move_line.get('lot_id')

                    else:  # if move.line id does not exist, create new record.
                        move_obj = stock_move.sudo().search([
                            ('picking_id', '=', req_params.get("picking_id")),
                            ('product_id', '=', move_line.get('product_id')),
                        ])

                        if move_line.get('product_package'):
                            package_obj = stock_quant_package.search(
                                [('name', '=', move_line.get('product_package'))], limit=1)
                            if not package_obj:
                                package_obj = stock_quant_package.create(
                                    {
                                        'name': move_line.get('product_package'),
                                        'package_use': 'disposable'
                                    })
                            package_id = package_obj.id

                        elif isinstance(move_line.get('product_packages_id'), int):
                            package_id = move_line.get('product_packages_id')

                        vals = {
                            'company_id': request.env.user.company_id.id,
                            'picking_id': stock_picking_obj.id,
                            'move_id': move_obj.id,
                            'product_id': move_obj.product_id.id,
                            # 'product_uom_qty': move_line.get('quantity_done'),
                            'qty_done': move_line.get('quantity_done'),
                            'product_uom_id': move_obj.product_uom.id,
                            'location_id': move_obj.location_id.id,
                            'location_dest_id': move_obj.location_dest_id.id,
                            'lot_id': lot_id,
                            'lot_name': lot_name,
                            'result_package_id': package_id
                        }
                        request.env['stock.move.line'].create(vals)

                # stock_picking_obj.state = 'done'
                stock_picking_obj.with_context(skip_immediate=True, skip_sms=True,
                                               skip_backorder=True,
                                               picking_ids_not_to_backorder=stock_picking_obj.ids
                                               ).button_validate()

                # ToDo: Check if it is a batch sync, change response.
                if 'batch_validate' in req_data:
                    return {'message': "Transfer is validated.", 'picking_id': stock_picking_obj.id,
                            "batch_validate": True}

                return {"status": True, 'message': "Transfer is validated.", 'picking_id': stock_picking_obj.id}

                # return valid_response({'message': "Transfer is validated.", 'picking_id': stock_picking_obj.id})

            else:
                # ToDo: Check if it is a batch sync, change response.
                if 'batch_validate' in req_data:
                    return {'code': "move_line_ids_empty", 'message': "Move lines are empty.",
                            'picking_id': stock_picking_obj.id, "batch_validate": True}
                return {"status": False, 'code': "move_line_ids_empty", 'message': "Move lines are empty.",
                        'picking_id': stock_picking_obj.id}

                # return invalid_response("move_line_ids_empty", "Move lines are empty.", 200)

    @validate_token
    @http.route("/api/post_picking_validate", type="json", auth="none", methods=["POST"], csrf=False)
    def post_picking_validate(self, **payload):
        _logger.info("/api/post_picking_validate payload: %s", payload)

        try:
            res = self.post_picking_validate_response_data(payload)

            if isinstance(res, list):
                if any(dictionary.get('batch_validate') == True for dictionary in res):
                    return res
                else:
                    return valid_response(res)

            elif isinstance(res, dict):
                if res['status']:
                    return valid_response(res)
                else:
                    return invalid_response(res['code'], res['message'], 200)

        except Exception as e:
            _logger.exception("Error while validating picking for payload: %s", payload)
            error_msg = 'Error while Validating Picking.'
            return invalid_response('bad_request', error_msg, 200)

    @validate_token
    @http.route("/api/batch_post_picking_validate", type="json", auth="none", methods=["POST"], csrf=False)
    def batch_post_picking_validate(self, **payload):
        _logger.info("/api/batch_post_picking_validate payload: %s", payload)

        try:
            # convert the bytes format to `list of dict` format
            req_data = json.loads(request.httprequest.data.decode())
            batch_res = []
            for data in req_data['data']:
                data['batch_validate'] = True
                batch_res.append(self.post_picking_validate(**data))
            return valid_response(batch_res)
        except Exception as e:
            _logger.exception("Error while validating batch picking for payload: %s", payload)
            error_msg = 'Error while validating batch picking.'
            return invalid_response('bad_request', error_msg, 200)

    @validate_token
    @http.route("/api/user_detail", type="json", auth="none", methods=["POST"], csrf=False)
    def post_user_detail(self, **payload):
        _logger.info("/api/user_detail POST payload: %s", payload)

        try:
            access_token = request.httprequest.headers.get("access-token")
            user_id = request.env['api.access_token'].sudo().search([('token', '=', access_token)], limit=1).user_id
            if user_id and request.httprequest.method == 'POST':
                # convert the bytes format to `list of dict` format
                req_data = json.loads(request.httprequest.data.decode())
                if 'name' in req_data['data'].keys() or 'image' in req_data['data'].keys():
                    if 'name' in req_data['data'].keys():
                        name = req_data['data']['name']
                        if name != user_id.name:
                            user_id.name = name
                    if 'image' in req_data['data'].keys():
                        image = req_data['data']['image']
                        if image != user_id.image_1920:
                            user_id.image_1920 = image
                    return valid_response({'message': "User Data Updated."})
                return invalid_response("no_user_data", "No name or image found.", 200)
        except Exception as e:
            _logger.exception("Error while updating user data for payload: %s", payload)
            error_msg = 'Error while updating user data.'
            return invalid_response('bad_request', error_msg, 200)

    @staticmethod
    def post_batch_validate_data(payload):

        package_id = False
        package_obj = False
        stock_quant_package = request.env['stock.quant.package']
        params = ["batch_id", "move_line_ids"]
        req_data = payload if len(payload) > 0 else json.loads(
            request.httprequest.data.decode())  # convert the bytes format to dict format
        req_params = {key: req_data.get(key) for key in params if req_data.get(key)}
        batch_id, move_line_ids = (
            req_params.get("batch_id"),
            req_params.get("move_line_ids")
        )

        _logger.info("Updating Batch Picking Transfers")
        stock_picking_batch = request.env['stock.picking.batch']
        stock_move = request.env['stock.move']
        stock_move_line = request.env['stock.move.line']
        stock_prod_lot = request.env['stock.lot']

        stock_picking_batch_obj = stock_picking_batch.sudo().search([('id', '=', req_params.get("batch_id"))])

        if stock_picking_batch_obj:
            if stock_picking_batch_obj.state == 'done':
                if 'sync_batch_pickings' in req_data:
                    return {'code': "already_validated", 'message': "This Batch is already done.",
                            'batch_id': stock_picking_batch_obj.id}
                return {'status': False, 'code': "already_validated", 'message': "This Batch is already done.",
                        'batch_id': stock_picking_batch_obj.id}
                # return invalid_response("already_validated", "This Batch is already done.", 200)

            if stock_picking_batch_obj.state == 'cancel':
                if 'sync_batch_pickings' in req_data:
                    return {'code': "batch_cancelled", 'message': "This Batch is Cancelled.",
                            'batch_id': stock_picking_batch_obj.id}
                return {'status': False, 'code': "batch_cancelled", 'message': "This Batch is Cancelled.",
                        'batch_id': stock_picking_batch_obj.id}
                # return invalid_response("batch_cancelled", "This Batch is Cancelled.", 200)

            if move_line_ids:
                for move_line in move_line_ids:

                    lot_detail = stock_prod_lot.sudo().search([
                        ('name', '=', move_line.get('lot_id')),
                        ('product_id', '=', move_line.get('product_id')),
                        ('company_id', '=', request.env.user.company_id.id)
                    ], limit=1)

                    lot_id = False
                    lot_name = False

                    if not lot_detail:
                        lot_detail = stock_prod_lot.create({
                            'name': move_line.get('lot_id'),
                            'product_id': move_line.get('product_id'),
                            'company_id': request.env.user.company_id.id,
                        })

                    if stock_picking_batch_obj.picking_type_id.code in ['outgoing', 'internal']:
                        # for Delivery Orders and Internal transfer
                        lot_id = lot_detail.id
                    if stock_picking_batch_obj.picking_type_id.code == 'incoming':  # for Receipts
                        if stock_picking_batch_obj.picking_type_id.use_existing_lots:  # Use Existing lots enabled
                            lot_id = lot_detail.id
                        else:  # Use Create New lots enabled
                            lot_name = move_line.get('lot_id')

                    if move_line.get("id"):  # if move.line id exists in the system.
                        move_line_obj = stock_move_line.sudo().browse(move_line.get("id"))

                        move_line_obj.reserved_uom_qty = 0
                        move_line_obj.qty_done = move_line.get('quantity_done')
                        move_line_obj.lot_id = lot_id
                        move_line_obj.lot_name = lot_name

                        if move_line.get('product_package'):
                            package_obj = stock_quant_package.search(
                                [('name', '=', move_line.get('product_package'))], limit=1)
                            if not package_obj:
                                package_obj = stock_quant_package.create(
                                    {
                                        'name': move_line.get('product_package'),
                                        'package_use': 'disposable'
                                    })
                            move_line_obj.result_package_id = package_obj.id
                        elif isinstance(move_line.get('product_packages_id'), int):
                            move_line_obj.result_package_id = move_line.get('product_packages_id')
                        # move_line_obj.result_package_id = move_line.get('product_packages_id')

                    else:  # if move.line id does not exist, create new record.
                        move_obj = stock_move.sudo().search([
                            ('picking_id', '=', move_line.get("picking_id")),
                            ('product_id', '=', move_line.get('product_id')),
                        ])

                        if move_line.get('product_package'):
                            package_obj = stock_quant_package.search(
                                [('name', '=', move_line.get('product_package'))], limit=1)
                            if not package_obj:
                                package_obj = stock_quant_package.create(
                                    {
                                        'name': move_line.get('product_package'),
                                        'package_use': 'disposable'
                                    })
                            package_id = package_obj.id
                        elif isinstance(move_line.get('product_packages_id'), int):
                            package_id = move_line.get('product_packages_id')

                        vals = {
                            'picking_id': move_line.get("picking_id"),
                            'batch_id': stock_picking_batch_obj.id,
                            'move_id': move_obj.id,
                            'product_id': move_obj.product_id.id,
                            'qty_done': move_line.get('quantity_done'),
                            'product_uom_id': move_obj.product_uom.id,
                            'location_id': move_obj.location_id.id,
                            'location_dest_id': move_obj.location_dest_id.id,
                            'lot_id': lot_id,
                            'lot_name': lot_name,
                            'result_package_id': package_id,
                        }
                        request.env['stock.move.line'].create(vals)

                stock_picking_batch_obj.action_done()

                if 'sync_batch_pickings' in req_data:
                    return {'code': "picking_ids_empty", 'message': "Pickings are empty.",
                            'batch_id': stock_picking_batch_obj.id}
                return {'status': False, 'code': "picking_ids_empty", 'message': "Pickings are empty.",
                        'batch_id': stock_picking_batch_obj.id}

                # stock_picking_objs = stock_picking_batch_obj.picking_ids

                # if stock_picking_objs:
                #     for stock_picking_obj in stock_picking_objs:
                #         stock_picking_obj.with_context(skip_immediate=True, skip_sms=True,
                #                                         skip_backorder=True,
                #                                         picking_ids_not_to_backorder=stock_picking_obj.ids
                #                                         ).button_validate()

                #     if 'sync_batch_pickings' in req_data:
                #         return {'code': "success", 'message': "Batch Transfer is validated.",
                #                 'batch_id': stock_picking_batch_obj.id}
                #     return {'status': True, 'code': "success", 'message': "Batch Transfer is validated.",
                #                 'batch_id': stock_picking_batch_obj.id}
                #     # return valid_response({'message': "Batch Transfer is validated.", 'batch_id': stock_picking_batch_obj.id})
                # else:
                #     if 'sync_batch_pickings' in req_data:
                #         return {'code': "picking_ids_empty", 'message': "Pickings are empty.",
                #                 'batch_id': stock_picking_batch_obj.id}
                #     return {'status': False, 'code': "picking_ids_empty", 'message': "Pickings are empty.",
                #                 'batch_id': stock_picking_batch_obj.id}
                # return invalid_response("picking_ids_empty", "Pickings are empty.", 200)

            else:
                if 'sync_batch_pickings' in req_data:
                    return {'code': "move_line_ids_empty", 'message': "Move lines are empty.",
                            'batch_id': stock_picking_batch_obj.id}
                return {'status': False, 'code': "move_line_ids_empty", 'message': "Move lines are empty.",
                        'batch_id': stock_picking_batch_obj.id}
                # return invalid_response("move_line_ids_empty", "Move lines are empty.", 200)
        else:
            if 'sync_batch_pickings' in req_data:
                return {'code': "batch_picking_not_exists",
                        'message': "This batch transfer was not found in the system.",
                        'batch_id': req_params.get("batch_id")}
            return {'status': False, 'code': "batch_picking_not_exists",
                    'message': "This batch transfer was not found in the system.",
                    'batch_id': req_params.get("batch_id")}
            # return invalid_response("move_line_ids_empty", "Move lines are empty.", 200)

    @validate_token
    @http.route("/api/post_batch_validate", type="json", auth="none", methods=["POST"], csrf=False)
    def post_batch_validate(self, **payload):
        _logger.info("/api/post_batch_validate payload: %s", payload)

        try:
            res = self.post_batch_validate_data(payload)
            for rec in res:
                if 'status' and 'batch_id' in rec:
                    return valid_response(res)
            else:
                return invalid_response(res['code'], res['message'], 200)

        except Exception as e:
            _logger.exception("Error while validating batch picking for payload: %s", payload)
            error_msg = 'Error while Validating Batch Picking.'
            return invalid_response('bad_request', error_msg, 200)

    @validate_token
    @http.route("/api/sync_batch_post_picking_validate", type="json", auth="none", methods=["POST"], csrf=False)
    def sync_batch_post_picking_validate(self, **payload):
        _logger.info("/api/sync_batch_post_picking_validate payload: %s", payload)

        try:
            req_data = json.loads(
                request.httprequest.data.decode())  # convert the bytes format to `list of dict` format
            batch_res = []
            for data in req_data['data']:
                data['sync_batch_pickings'] = True
                batch_res.append(self.post_batch_validate(**data))
            return valid_response(batch_res)
        except Exception as e:
            _logger.exception("Error while validating batch picking for payload: %s", payload)
            error_msg = 'Error while updating user data.'
            return invalid_response('bad_request', error_msg, 200)

    @staticmethod
    def post_stock_quants_data(payload):

        params = ["stock_quant"]
        req_data = payload if len(payload) > 0 else json.loads(
            request.httprequest.data.decode())
        req_params = {key: req_data.get(key) for key in params if req_data.get(key)}
        stock_quant_data = req_params.get("stock_quant")

        _data_included_in_body = all([stock_quant_data])
        if not _data_included_in_body:
            return {"status": False, 'code': "post_data_error", 'message': "Data is not valid, please check again",
                    'picking_id': req_data['stock_quant']}
        else:
            _logger.info("Updating Stock Quant Data")
            stock_count = 0
            product_package = False
            stock_quant_obj = False
            lot_id = False
            owner_id = False
            stock_prod_lot = request.env['stock.lot']
            stock_quant = request.env['stock.quant']
            stock_quant_package = request.env['stock.quant.package']

            if stock_quant_data:
                for quant in stock_quant_data:
                    if isinstance(quant.get('package_id'), int):
                        product_package = quant.get('package_id')
                    elif not quant.get('package_id'):
                        product_package = False
                    else:
                        package_obj = stock_quant_package.search(
                            [('name', '=', quant.get('package_id'))], limit=1)
                        if not package_obj:
                            package_obj = stock_quant_package.create(
                                {
                                    'name': quant.get('package_id'),
                                    'package_use': 'disposable'
                                })
                        product_package = package_obj.id

                    if not quant.get('package_id'):
                        lot_detail = stock_prod_lot.sudo().search([
                            ('name', '=', quant.get('lot_id')),
                            ('product_id', '=', quant.get('product_id')),
                            ('company_id', '=', request.env.user.company_id.id)], limit=1)

                        if not lot_detail:
                            lot_detail = stock_prod_lot.create({
                                'name': quant.get('lot_id'),
                                'product_id': quant.get('product_id'),
                                'company_id': request.env.user.company_id.id,
                            })
                            lot_id = lot_detail.id

                    vals = {
                        'location_id': quant.get('location_id'),
                        'product_id': quant.get('product_id'),
                        'lot_id': lot_id,
                        'package_id': product_package,
                        'owner_id': quant.get('owner_id'),
                        'inventory_quantity': quant.get('inventory_quantity'),
                        'inventory_date': quant.get('inventory_date'),
                        'user_id': quant.get('user_id'),
                    }
                    if not quant.get('owner_id'):
                        owner_id = False
                    else:
                        owner_id = quant.get('owner_id')

                    domain = [('location_id.usage', 'in', ['internal', 'transit']),
                              ('location_id', '=', quant.get('location_id')),
                              ('product_id', '=', quant.get('product_id')),
                              ('lot_id', '=', lot_id), ('package_id', '=', product_package),
                              ('owner_id', '=', owner_id), ('company_id', '=', request.env.user.company_id.id)]

                    stock_quant_available = stock_quant.sudo().search(domain, limit=1)
                    if stock_quant_available:
                        stock_quant_available.write(vals)
                        stock_quant_available.action_apply_inventory()
                        stock_count = stock_count + 1
                    else:
                        stock_quant_obj = stock_quant.create(vals)
                        if stock_quant_obj:
                            stock_quant_obj.action_apply_inventory()
                            stock_count = stock_count + 1
                            # return {"status": True, 'message': "Stock quant is created", 'quant_id': stock_quant_obj.id}
                        else:
                            return {"status": False, 'code': "not_stock_quant_created",
                                    'message': "Stock quant is not created",
                                    'product_id': quant.get('product_id'), 'location_id': quant.get('location_id')}
                    if stock_count == len(stock_quant_data):
                        return {"status": True, 'message': "Stock quant is created and updated with quantity"}
            else:
                return {"status": False, 'code': "stock_quant_data", 'message': "Stock quant datas are empty."}

    @validate_token
    @http.route("/api/post_stock_quants", type="json", auth="none", methods=["POST"], csrf=False)
    def post_stock_quants(self, **payload):
        """
            create stock quant info.
        """
        _logger.info("/api/post_stock_quants POST payload: %s", payload)
        try:
            response_data = self.post_stock_quants_data(payload)
            if isinstance(response_data, dict):
                if response_data['status']:
                    return valid_response(response_data)
                else:
                    return invalid_response(response_data['code'], response_data['message'])
        except Exception as e:
            _logger.exception(
                "Error while creating stock quants data: %s", payload)
            error_msg = 'Error while creating stock quants data'
            return invalid_response('bad_request', error_msg, 200)
