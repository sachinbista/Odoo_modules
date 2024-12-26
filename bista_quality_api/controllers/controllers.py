# -*- coding: utf-8 -*-
import logging
import json
import ast
import re

from odoo import http
from odoo.http import request
from odoo.addons.bista_wms_api.common import invalid_response, valid_response
from odoo.addons.bista_wms_api.controllers.controllers import validate_token
from odoo.http import Response
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT

_logger = logging.getLogger(__name__)


class BistaQualityApi(http.Controller):
    """Quality Management System Controller"""

    @validate_token
    @http.route("/api/get_quality_dashboard", type="http", auth="none", methods=["GET"], csrf=False)
    def get_quality_dashboard(self, **payload):
        """Get quality check, quality alert, control point Data for Dashboard."""

        _logger.info("/api/get_quality_dashboard payload: %s", payload)

        try:
            res = {}
            control_point_count = request.env['quality.point'].search_count([
                ('company_id', '=', request.env.user.company_id.id)
            ])
            quality_check_count = request.env['quality.check'].search_count([
                ('quality_state', '=', 'none'), ('company_id', '=', request.env.user.company_id.id)
            ])
            quality_alert_count = request.env['quality.alert'].search_count([
                ('company_id', '=', request.env.user.company_id.id)
            ])

            res.update({
                'control_point_count': control_point_count,
                'quality_check_count': quality_check_count,
                'quality_alert_count': quality_alert_count,
                # 'quality_dashboard_sum': control_point_count + quality_check_count + quality_alert_count
            })
            return valid_response(res)

        except Exception as e:
            _logger.exception("Error while getting quality dashboard data", e)
            error_msg = 'Error while getting quality dashboard data.'
            return invalid_response('bad_request', error_msg, 200)

    @validate_token
    @http.route("/api/get_control_point", type="http", auth="none", methods=["GET"], csrf=False)
    def get_control_point(self, **payload):
        """Get quality control point records"""

        _logger.info("/api/get_control_point payload: %s", payload)

        detail_api_response = {'status': True, 'message': ""}
        payload_data = payload
        try:
            response_data = []
            control_point = request.env['quality.point']
            control_point_objs = False
            if 'id' in payload_data or 'name' in payload_data:
                if 'id' in payload_data:
                    if payload_data['id']:
                        control_point_objs = control_point.sudo().browse(int(payload_data['id']))
                elif 'name' in payload_data:
                    if payload_data['name']:
                        control_point_objs = control_point.sudo().search([('name', '=', payload_data['name'])])
            else:
                control_point_objs = control_point.sudo().search([('company_id', '=', request.env.user.company_id.id)])
            if control_point_objs:
                for control_point_obj in control_point_objs:
                    products = []
                    product_categories = []
                    operations = []
                    for product_id in control_point_obj.product_ids:
                        products.append({
                            'id': product_id.id,
                            'name': product_id.display_name,
                            'code': product_id.default_code or "",
                        })
                    for product_category in control_point_obj.product_category_ids:
                        product_categories.append({
                            'id': product_category.id,
                            'name': product_category.name,
                            'complete_name': product_category.complete_name or "",
                        })
                    for picking_type_id in control_point_obj.picking_type_ids:
                        operations.append({
                            'id': picking_type_id.id,
                            'name': picking_type_id.name,
                        })
                    response_data.append({
                        'id': control_point_obj.id,
                        'name': control_point_obj.name,
                        'title': control_point_obj.title or "",
                        'products': products,
                        'product_categories': product_categories,
                        'operations': operations,
                        'measure_on': control_point_obj.measure_on or "",
                        'measure_frequency_type': control_point_obj.measure_frequency_type or "",
                        'measure_frequency_value': control_point_obj.measure_frequency_value or "",
                        'measure_frequency_unit_value': control_point_obj.measure_frequency_unit_value or "",
                        'measure_frequency_unit': control_point_obj.measure_frequency_unit or "",
                        'test_type': control_point_obj.test_type_id.name,
                        'norm': control_point_obj.norm or "",
                        'norm_unit': control_point_obj.norm_unit or "",
                        'tolerance_min': control_point_obj.tolerance_min or "",
                        'tolerance_max': control_point_obj.tolerance_max or "",
                        'team': control_point_obj.team_id.name,
                        'company': control_point_obj.company_id.name,
                        'create_uid': [str(control_point_obj.create_uid.id),
                                       control_point_obj.create_uid.name] if control_point_obj.create_uid else [],
                        'create_date': control_point_obj.create_date.strftime(DEFAULT_SERVER_DATETIME_FORMAT),
                        'write_uid': [str(control_point_obj.write_uid.id),
                                      control_point_obj.write_uid.name] if control_point_obj.write_uid else [],
                        'write_date': control_point_obj.write_date.strftime(DEFAULT_SERVER_DATETIME_FORMAT),
                    })
                if payload_data.get('detail_api', False):
                    detail_api_response.update({'status': "True", 'response_data': response_data})
                    return str(detail_api_response)
                return valid_response(response_data)
            else:
                if payload_data.get('detail_api', False):
                    detail_api_response.update({'status': "False",
                                                'message': "No control point record found.",
                                                'response_data': response_data})
                    return str(detail_api_response)
                return invalid_response('not_found', 'No control point record found.')

        except Exception as e:
            _logger.exception("Error while getting control point record", e)
            error_msg = 'Error while getting control point record.'
            if payload_data.get('detail_api', False):
                detail_api_response.update({'status': "False",
                                            'message': error_msg,
                                            'response_data': []})
                return str(detail_api_response)
            return invalid_response('bad_request', error_msg, 200)

    @validate_token
    @http.route("/api/get_quality_check", type="http", auth="none", methods=["GET"], csrf=False)
    def get_quality_check(self, **payload):
        """Get quality check records"""

        _logger.info("/api/get_quality_check payload: %s", payload)

        detail_api_response = {'status': True, 'message': ""}
        payload_data = payload
        try:
            response_data = []
            quality_check = request.env['quality.check']
            quality_check_objs = False
            if 'id' in payload_data or 'name' in payload_data:
                if 'id' in payload_data:
                    if payload_data['id']:
                        quality_check_objs = quality_check.sudo().browse(int(payload_data['id']))
                elif 'name' in payload_data:
                    if payload_data['name']:
                        quality_check_objs = quality_check.sudo().search([('name', '=', payload_data['name'])])
            else:
                quality_check_objs = quality_check.sudo().search([('company_id', '=', request.env.user.company_id.id)])
            if quality_check_objs:
                for quality_check_obj in quality_check_objs:
                    activity_ids = []
                    alert_ids = []
                    message_partner_ids = []
                    for activity_id in quality_check_obj.activity_ids:
                        activity_ids.append({
                            'id': activity_id.id,
                            'name': activity_id.display_name,
                        })
                    for alert_id in quality_check_obj.alert_ids:
                        alert_ids.append({
                            'id': alert_id.id,
                            'name': alert_id.name,
                        })
                    for message_partner_id in quality_check_obj.message_partner_ids:
                        message_partner_ids.append({
                            'id': message_partner_id.id,
                            'name': message_partner_id.name,
                        })
                    response_data.append({
                        'id': quality_check_obj.id,
                        'name': quality_check_obj.name,
                        'title': quality_check_obj.title or "",
                        'product_id': [str(quality_check_obj.product_id.id),
                                       quality_check_obj.product_id.name] if quality_check_obj.product_id else [],

                        'activity_date_deadline': quality_check_obj.activity_date_deadline or '',
                        'activity_exception_decoration': quality_check_obj.activity_exception_decoration or '',
                        'activity_exception_icon': quality_check_obj.activity_exception_icon or '',
                        'activity_ids': activity_ids or [],
                        'activity_state': quality_check_obj.activity_state or '',
                        'activity_summary': quality_check_obj.activity_summary or '',
                        'activity_type_icon': quality_check_obj.activity_type_icon or '',
                        'activity_type_id': [str(quality_check_obj.activity_type_id.id),
                                             quality_check_obj.activity_type_id.name] if quality_check_obj.activity_type_id else [],
                        'activity_user_id': [str(quality_check_obj.activity_user_id.id),
                                             quality_check_obj.activity_user_id.name] if quality_check_obj.activity_user_id else [],
                        'additional_note': quality_check_obj.additional_note or '',
                        'alert_count': quality_check_obj.alert_count or '',
                        'alert_ids': alert_ids or [],
                        'batch_id': ([str(quality_check_obj.batch_id.id),
                                     quality_check_obj.batch_id.name] if quality_check_obj.batch_id else []) if 'batch_id' in quality_check_obj._fields else [],
                        'company_id': quality_check_obj.company_id.name or '' if quality_check_obj.company_id else [],
                        'control_date': quality_check_obj.control_date.strftime(DEFAULT_SERVER_DATETIME_FORMAT) if quality_check_obj.control_date else '',
                        'failure_message': quality_check_obj.failure_message or '',
                        'has_message': quality_check_obj.has_message or False,
                        'is_lot_tested_fractionally': quality_check_obj.is_lot_tested_fractionally or '',
                        'lot_id': [str(quality_check_obj.lot_id.id),
                                   quality_check_obj.lot_id.name] if quality_check_obj.lot_id else [],
                        'lot_line_id': [str(quality_check_obj.lot_line_id.id),
                                        quality_check_obj.lot_line_id.name] if quality_check_obj.lot_line_id else [],
                        'lot_name': quality_check_obj.lot_name or '',
                        'measure': quality_check_obj.measure or '',
                        'measure_on': quality_check_obj.measure_on or '',
                        'measure_success': quality_check_obj.measure_success or '',
                        'message_attachment_count': quality_check_obj.message_attachment_count or '',
                        'message_has_error': quality_check_obj.message_has_error or False,
                        'message_has_error_counter': quality_check_obj.message_has_error_counter or '',
                        'message_has_sms_error': quality_check_obj.message_has_sms_error or False,
                        # 'message_ids': quality_check_obj.message_ids or '',
                        'message_is_follower': quality_check_obj.message_is_follower or False,
                        # 'message_main_attachment_id': quality_check_obj.message_main_attachment_id or '',
                        'message_needaction': quality_check_obj.message_needaction or False,
                        'message_needaction_counter': quality_check_obj.message_needaction_counter or '',
                        'message_partner_ids': message_partner_ids or [],

                        # 'message_unread': quality_check_obj.message_unread or '',
                        # message_unread from v15 has been removed from v16

                        # 'message_unread_counter': quality_check_obj.message_unread_counter or '',
                        # message_unread_counter from v15 has been removed from v16

                        'move_line_id': [str(quality_check_obj.move_line_id.id)] if quality_check_obj.move_line_id else [],
                        'my_activity_date_deadline': quality_check_obj.my_activity_date_deadline or '',
                        'norm_unit': quality_check_obj.norm_unit or '',
                        'note': re.sub(re.compile('<.*?>'), '', quality_check_obj.note) if quality_check_obj.note else '',
                        'partner_id': [str(quality_check_obj.partner_id.id),
                                       quality_check_obj.partner_id.name] if quality_check_obj.partner_id else [],
                        'picking_id': [str(quality_check_obj.picking_id.id),
                                       quality_check_obj.picking_id.name] if quality_check_obj.picking_id else [],
                        'picture': '/web/image?model=quality.check&field=picture&id={}'.format(quality_check_obj.id) if quality_check_obj.picture else '',
                        'point_id': [str(quality_check_obj.point_id.id),
                                     quality_check_obj.point_id.name] if quality_check_obj.point_id else [],
                        'product_tracking': quality_check_obj.product_tracking or '',
                        'qty_line': quality_check_obj.qty_line or '',
                        'qty_tested': quality_check_obj.qty_tested or '',
                        'qty_to_test': quality_check_obj.qty_to_test or '',
                        'quality_state': quality_check_obj.quality_state or '',
                        'show_lot_text': quality_check_obj.show_lot_text or '',
                        'team_id': [str(quality_check_obj.team_id.id),
                                    quality_check_obj.team_id.name] if quality_check_obj.team_id else [],
                        'test_type': quality_check_obj.test_type or '',
                        'test_type_id': [str(quality_check_obj.test_type_id.id),
                                         quality_check_obj.test_type_id.name] if quality_check_obj.test_type_id else [],
                        'testing_percentage_within_lot': quality_check_obj.testing_percentage_within_lot or '',
                        'tolerance_max': quality_check_obj.tolerance_max or '',
                        'tolerance_min': quality_check_obj.tolerance_min or '',
                        'uom_id': [str(quality_check_obj.uom_id.id),
                                   quality_check_obj.uom_id.name] if quality_check_obj.uom_id else [],
                        'user_id': [str(quality_check_obj.user_id.id),
                                    quality_check_obj.user_id.name] if quality_check_obj.user_id else [],
                        'warning_message': quality_check_obj.warning_message or '',
                        # 'website_message_ids': quality_check_obj.website_message_ids or '',

                        'create_uid': [str(quality_check_obj.create_uid.id),
                                       quality_check_obj.create_uid.name] if quality_check_obj.create_uid else [],
                        'create_date': quality_check_obj.create_date.strftime(DEFAULT_SERVER_DATETIME_FORMAT),
                        'write_uid': [str(quality_check_obj.write_uid.id),
                                      quality_check_obj.write_uid.name] if quality_check_obj.write_uid else [],
                        'write_date': quality_check_obj.write_date.strftime(DEFAULT_SERVER_DATETIME_FORMAT),
                    })
                if payload_data.get('detail_api', False):
                    detail_api_response.update({'status': "True", 'response_data': response_data})
                    return str(detail_api_response)
                return valid_response(response_data)
            else:
                if payload_data.get('detail_api', False):
                    detail_api_response.update({'status': "False",
                                                'message': "No quality check record found.",
                                                'response_data': response_data})
                    return str(detail_api_response)
                return invalid_response('not_found', 'No quality check record found.')

        except Exception as e:
            _logger.exception("Error while getting quality check record", e)
            error_msg = 'Error while getting quality check record.'
            if payload_data.get('detail_api', False):
                detail_api_response.update({'status': "False",
                                            'message': error_msg,
                                            'response_data': []})
                return str(detail_api_response)
            return invalid_response('bad_request', error_msg, 200)

    @validate_token
    @http.route("/api/get_quality_alert", type="http", auth="none", methods=["GET"], csrf=False)
    def get_quality_alert(self, **payload):
        """Get quality alert records"""

        _logger.info("/api/get_quality_alert payload: %s", payload)

        detail_api_response = {'status': True, 'message': ""}
        payload_data = payload
        try:
            response_data = []
            quality_alert = request.env['quality.alert']
            quality_alert_objs = False
            if 'id' in payload_data or 'name' in payload_data:
                if 'id' in payload_data:
                    if payload_data['id']:
                        quality_alert_objs = quality_alert.sudo().browse(int(payload_data['id']))
                elif 'name' in payload_data:
                    if payload_data['name']:
                        quality_alert_objs = quality_alert.sudo().search([('name', '=', payload_data['name'])])
            else:
                quality_alert_objs = quality_alert.sudo().search([('company_id', '=', request.env.user.company_id.id)])
            if quality_alert_objs:
                for quality_alert_obj in quality_alert_objs:
                    activity_ids = []
                    message_partner_ids = []
                    tag_ids = []
                    for activity_id in quality_alert_obj.activity_ids:
                        activity_ids.append({
                            'id': activity_id.id,
                            'name': activity_id.display_name,
                        })
                    for message_partner_id in quality_alert_obj.message_partner_ids:
                        message_partner_ids.append({
                            'id': message_partner_id.id,
                            'name': message_partner_id.name,
                        })
                    for tag_id in quality_alert_obj.tag_ids:
                        tag_ids.append({
                            'id': tag_id.id,
                            'name': tag_id.name,
                        })

                    response_data.append({
                        'id': quality_alert_obj.id,
                        'name': quality_alert_obj.name,
                        'title': quality_alert_obj.title or "",

                        # boolean(6)
                        'has_message': quality_alert_obj.has_message or False,
                        'message_has_error': quality_alert_obj.message_has_error or False,
                        'message_has_sms_error': quality_alert_obj.message_has_sms_error or False,
                        'message_is_follower': quality_alert_obj.message_is_follower or False,
                        'message_needaction': quality_alert_obj.message_needaction or False,

                        # 'message_unread': quality_alert_obj.message_unread or "",
                        # message_unread from v15 has been removed from v16

                        # char(7)
                        'activity_exception_icon': quality_alert_obj.activity_exception_icon or "",
                        'activity_summary': quality_alert_obj.activity_summary or "",
                        'activity_type_icon': quality_alert_obj.activity_type_icon or "",
                        'display_name': quality_alert_obj.display_name or "",
                        'email_cc': quality_alert_obj.email_cc or "",
                        # date(2)
                        'activity_date_deadline': quality_alert_obj.activity_date_deadline or "",
                        'my_activity_date_deadline': quality_alert_obj.my_activity_date_deadline or "",
                        # datetime(5)
                        'date_assign': quality_alert_obj.date_assign or "",
                        'date_close': quality_alert_obj.date_close or "",
                        # html(3)
                        'action_corrective': quality_alert_obj.action_corrective or "",
                        'action_preventive': quality_alert_obj.action_preventive or "",
                        'description': quality_alert_obj.description or "",
                        # integer(5)
                        'message_attachment_count': quality_alert_obj.message_attachment_count or 0,
                        'message_has_error_counter': quality_alert_obj.message_has_error_counter or 0,
                        'message_needaction_counter': quality_alert_obj.message_needaction_counter or 0,

                        # 'message_unread_counter': quality_alert_obj.message_unread_counter or 0,
                        # message_unread_counter from v15 has been removed from v16

                        # many2many(2)
                        'message_partner_ids': message_partner_ids or [],
                        'tag_ids': tag_ids or [],
                        # many2one(16)
                        'activity_type_id': [str(quality_alert_obj.activity_type_id.id),
                                             quality_alert_obj.activity_type_id.name] if quality_alert_obj.activity_type_id else [],
                        'activity_user_id': [str(quality_alert_obj.activity_user_id.id),
                                             quality_alert_obj.activity_user_id.name] if quality_alert_obj.activity_user_id else [],
                        'check_id': [str(quality_alert_obj.check_id.id),
                                     quality_alert_obj.check_id.name] if quality_alert_obj.check_id else [],
                        'lot_id': [str(quality_alert_obj.lot_id.id),
                                   quality_alert_obj.lot_id.name] if quality_alert_obj.lot_id else [],
                        'message_main_attachment_id': [str(quality_alert_obj.message_main_attachment_id.id),
                                                       quality_alert_obj.message_main_attachment_id.name] if quality_alert_obj.message_main_attachment_id else [],
                        'partner_id': [str(quality_alert_obj.partner_id.id),
                                       quality_alert_obj.partner_id.name] if quality_alert_obj.partner_id else [],
                        'picking_id': [str(quality_alert_obj.picking_id.id),
                                       quality_alert_obj.picking_id.name] if quality_alert_obj.picking_id else [],
                        'product_id': [str(quality_alert_obj.product_id.id),
                                       quality_alert_obj.product_id.name] if quality_alert_obj.product_id else [],
                        'product_tmpl_id': [str(quality_alert_obj.product_tmpl_id.id),
                                            quality_alert_obj.product_tmpl_id.name] if quality_alert_obj.product_tmpl_id else [],
                        'workcenter_id': [str(quality_alert_obj.workcenter_id.id),
                                          quality_alert_obj.workcenter_id.name] if 'workcenter_id' in quality_alert._fields and quality_alert_obj.workcenter_id else [],
                        'reason_id': [str(quality_alert_obj.reason_id.id),
                                      quality_alert_obj.reason_id.name] if quality_alert_obj.reason_id else [],
                        'stage_id': [str(quality_alert_obj.stage_id.id),
                                     quality_alert_obj.stage_id.name] if quality_alert_obj.stage_id else [],
                        'team_id': [str(quality_alert_obj.team_id.id),
                                    quality_alert_obj.team_id.name] if quality_alert_obj.team_id else [],
                        'user_id': [str(quality_alert_obj.user_id.id),
                                    quality_alert_obj.user_id.name] if quality_alert_obj.user_id else [],
                        # one2many(4)
                        'activity_ids': activity_ids or [],
                        # selection(3)
                        'activity_exception_decoration': quality_alert_obj.activity_exception_decoration or "",
                        'activity_state': quality_alert_obj.activity_state or "",
                        'priority': quality_alert_obj.priority or "",

                        # 'message_ids': quality_alert_obj.message_ids or '',
                        # 'website_message_ids': quality_alert_obj.website_message_ids or '',

                        'create_uid': [str(quality_alert_obj.create_uid.id),
                                       quality_alert_obj.create_uid.name] if quality_alert_obj.create_uid else [],
                        'create_date': quality_alert_obj.create_date.strftime(DEFAULT_SERVER_DATETIME_FORMAT),
                        'write_uid': [str(quality_alert_obj.write_uid.id),
                                      quality_alert_obj.write_uid.name] if quality_alert_obj.write_uid else [],
                        'write_date': quality_alert_obj.write_date.strftime(DEFAULT_SERVER_DATETIME_FORMAT),
                    })
                if payload_data.get('detail_api', False):
                    detail_api_response.update({'status': "True", 'response_data': response_data})
                    return str(detail_api_response)
                return valid_response(response_data)
            else:
                if payload_data.get('detail_api', False):
                    detail_api_response.update({'status': "False",
                                                'message': "No quality check record found.",
                                                'response_data': response_data})
                    return str(detail_api_response)
                return invalid_response('not_found', 'No quality alert record found.')

        except Exception as e:
            _logger.exception("Error while getting quality alert record", e)
            error_msg = 'Error while getting quality alert record.'
            if payload_data.get('detail_api', False):
                detail_api_response.update({'status': "False",
                                            'message': error_msg,
                                            'response_data': []})
                return str(detail_api_response)
            return invalid_response('bad_request', error_msg, 200)

    @validate_token
    @http.route("/api/get_quality_alert_stage", type="http", auth="none", methods=["GET"], csrf=False)
    def get_quality_alert_stage(self, **payload):
        """Get quality alert stage records"""

        # _logger.info("/api/get_quality_alert_stage payload: %s", payload)

        detail_api_response = {'status': True, 'message': ""}
        payload_data = payload
        try:
            response_data = []
            quality_alert_stage = request.env['quality.alert.stage']
            alert_stage_objs = quality_alert_stage.sudo().search([])
            if alert_stage_objs:
                for alert_stage_obj in alert_stage_objs:
                    team = []
                    for team_id in alert_stage_obj.team_ids:
                        team.append({
                            'id': team_id.id,
                            'name': team_id.display_name,
                        })
                    response_data.append({
                        'id': alert_stage_obj.id,
                        'name': alert_stage_obj.name,
                        'sequence': alert_stage_obj.sequence or "",
                        'done': alert_stage_obj.done or "",
                        'folded': alert_stage_obj.folded or "",
                        'team': team,
                    })
                if payload_data.get('detail_api', False):
                    detail_api_response.update({'response_data': response_data})
                    return detail_api_response
                return valid_response(response_data)
            else:
                if payload_data.get('detail_api', False):
                    detail_api_response.update({'status': False,
                                                'message': "No quality alert stage record found.",
                                                'response_data': response_data})
                    return detail_api_response
                return invalid_response('not_found', 'No quality alert stage record found.')

        except Exception as e:
            _logger.exception("Error while getting quality alert stage record", e)
            error_msg = 'Error while getting quality alert stage record.'
            if payload_data.get('detail_api', False):
                detail_api_response.update({'status': False,
                                            'message': error_msg,
                                            'response_data': []})
                return detail_api_response
            return invalid_response('bad_request', error_msg, 200)

    @validate_token
    @http.route("/api/get_quality_details", type="http", auth="none", methods=["GET"], csrf=False)
    def get_quality_details(self, **payload):
        """Get detailed records of quality control point, quality checks & quality alerts records"""

        _logger.info("/api/get_quality_details payload: %s", payload)

        response_data = {}
        payload_data = payload

        payload_data.update({'detail_api': True})

        quality_control_point_data = self.get_control_point(**payload_data)
        if isinstance(quality_control_point_data, Response):
            quality_control_point_data = ast.literal_eval(quality_control_point_data.data.decode("utf-8"))
            response_data.update({
                'control_point_status': ast.literal_eval(quality_control_point_data.get('status', False)),
                'control_point_message': quality_control_point_data.get('message', ""),
                'control_point': quality_control_point_data.get('response_data', [])
            })

        quality_check_data = self.get_quality_check(**payload_data)
        if isinstance(quality_check_data, Response):
            quality_check_data = ast.literal_eval(quality_check_data.data.decode("utf-8"))
            response_data.update({
                'quality_check_status': ast.literal_eval(quality_check_data.get('status', False)),
                'quality_check_message': quality_check_data.get('message', ""),
                'quality_check': quality_check_data.get('response_data', [])
            })

        quality_alert_data = self.get_quality_alert(**payload_data)
        if isinstance(quality_alert_data, Response):
            quality_alert_data = ast.literal_eval(quality_alert_data.data.decode("utf-8"))
            response_data.update({
                'quality_alert_status': ast.literal_eval(quality_alert_data.get('status', False)),
                'quality_alert_message': quality_alert_data.get('message', ""),
                'quality_alert': quality_alert_data.get('response_data', [])
            })

        # quality_alert_stage_data = self.get_quality_alert_stage(**payload_data)
        # response_data.update({
        #     'quality_alert_stage_status': quality_alert_stage_data.get('status', False),
        #     'quality_alert_stage_message': quality_alert_stage_data.get('message', ""),
        #     'quality_alert_stage': quality_alert_stage_data.get('response_data', [])
        # })

        return valid_response(response_data)

    #######################################
    # POST APIs
    #######################################

    @staticmethod
    def post_quality_state_quality_data(req_data):
        def qua_chk_res(status=False, message="", rec_id=0):
            return {
                'status': status,
                'message': message,
                'record_id': rec_id
            }
        quality_res = []
        quality_check_list = req_data['data']['quality_check'] if req_data.get('data', False) else req_data.get('quality_check', [])
        for quality_check_dict in quality_check_list:
            if quality_check_dict['id']:
                quality_check_obj = request.env['quality.check'].sudo().search(
                    [('id', '=', quality_check_dict['id'])]
                )
                if quality_check_obj:
                    if quality_check_dict['state'] == "pass":
                        quality_check_obj.do_pass()
                        quality_res.append(qua_chk_res(True, "Quality check updated to passed.", quality_check_obj.id))
                    elif quality_check_dict['state'] == "fail":
                        quality_check_obj.do_fail()
                        quality_res.append(qua_chk_res(True, "Quality check updated to failed.", quality_check_obj.id))
                    else:
                        quality_res.append(qua_chk_res(False, "Error updating quality check.", quality_check_obj.id))
                else:
                    quality_res.append(qua_chk_res(False, "Quality check record not found.", quality_check_dict['id']))
        return quality_res
    
    @validate_token
    @http.route("/api/post_quality_state", type="json", auth="none", methods=["POST"], csrf=False)
    def post_quality_state(self, **payload):
        _logger.info("/api/post_quality_state POST payload: %s", payload)
        try:
            req_data = payload if len(payload) > 0 else json.loads(
                request.httprequest.data.decode())  # convert the bytes format to dict format
            _logger.info("/api/post_quality_state POST req_data: %s", req_data)

            quality_res = []
            if 'quality_alert' in req_data['data'].keys() and len(req_data['data']['quality_alert']):
                quality_alert_list = req_data['data']['quality_alert']
                for quality_alert_dict in quality_alert_list:
                    if quality_alert_dict['id']:
                        quality_alert_obj = request.env['quality.alert'].sudo().search(
                            [('id', '=', quality_alert_dict['id'])]
                        )
                        if quality_alert_obj:
                            alert_stage_obj = request.env['quality.alert.stage'].sudo().search(
                                [('id', '=', quality_alert_dict['stage_id'])])
                            if alert_stage_obj:
                                quality_alert_obj.stage_id = alert_stage_obj.id
                                quality_res.append({
                                    'status': True,
                                    'message': "Quality alert stage updated to %s." % alert_stage_obj.name,
                                    'record_id': quality_alert_obj.id
                                })
                            else:
                                quality_res.append({
                                    'status': False,
                                    'message': "Error while updating quality alert stage.",
                                    'record_id': quality_alert_obj.id
                                })
                        else:
                            quality_res.append({
                                'status': False,
                                'message': "Quality alert record not found.",
                                'record_id': quality_alert_dict['id']
                            })

            if 'quality_check' in req_data['data'].keys() and len(req_data['data']['quality_check']):
                quality_res += self.post_quality_state_quality_data(req_data)

            if len(quality_res) == 0:
                quality_res.append({'message': "No quality check/alert record updated."})
                error_msg = "No quality check/alert record updated."
                return invalid_response('bad_request', error_msg, 200)

            return valid_response(quality_res)

        except Exception as e:
            _logger.exception("Error while updating quality for payload: %s", payload)
            error_msg = 'Error while updating quality data.'
            return invalid_response('bad_request', error_msg, 200)
