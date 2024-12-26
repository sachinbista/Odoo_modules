# -*- coding: utf-8 -*-
import logging
import json

from odoo import http
from odoo.http import request
from odoo.addons.bista_wms_api.controllers.controllers import BistaWmsApi
from odoo.addons.bista_wms_api.controllers.controllers import validate_token
from .controllers import BistaQualityApi

_logger = logging.getLogger(__name__)


class BistaWmsApiInherit(BistaWmsApi):

    @staticmethod
    def _get_dashboard_values(self):
        res = super()._get_dashboard_values(self=self)
        quality_modules_installed = False
        # control_point_count = 0
        # quality_check_count = 0
        # quality_alert_count = 0
        quality_dashboard_sum = 0

        try:
            quality_modules = request.env['ir.module.module'].sudo().search([
                ('name', 'in', ['quality', 'quality_control', 'bista_wms_api'])
            ])
            if quality_modules:
                quality_modules_installed = True
            res.update({
                'quality_modules_installed': quality_modules_installed
            })

            control_point_count = request.env['quality.point'].search_count([
                ('company_id', '=', request.env.user.company_id.id)])
            quality_check_count = request.env['quality.check'].search_count([
                ('quality_state', '=', 'none'), ('company_id', '=', request.env.user.company_id.id)])
            quality_alert_count = request.env['quality.alert'].search_count([
                ('stage_id.name', '=', 'New'), ('company_id', '=', request.env.user.company_id.id)])

            quality_dashboard_sum = control_point_count + quality_check_count + quality_alert_count

        except Exception as e:
            _logger.exception("Error while getting quality dashboard data", e)
            # error_msg = 'Error while getting quality dashboard data.'
            # return invalid_response('bad_request', error_msg, 200)

        res.update({
            # 'control_point_count': control_point_count,
            # 'quality_check_count': quality_check_count,
            # 'quality_alert_count': quality_alert_count,
            'quality_dashboard_sum': quality_dashboard_sum
        })
        return res

    @staticmethod
    def get_picking_detail_response_data(self, response_data, stock_picking_objs):
        """GET API: Adding quality data in get_picking_detail """

        res = super().get_picking_detail_response_data(self, response_data, stock_picking_objs)

        for rec in res:
            stock_picking_obj = stock_picking_objs.filtered(lambda q: q.id == rec['id'])

            rec['check_ids'] = []

            if stock_picking_obj.check_ids:
                for value in stock_picking_obj.check_ids:
                    rec['check_ids'].append({
                        'id': value.id if value.id else "",
                        'name': value.name if value.name else "",
                        'user_id': [str(value.user_id.id),
                                    value.user_id.name] if value.user_id else [],
                        'product_id': [str(value.product_id.id),
                                       value.product_id.name] if value.product_id else [],
                        'team_id': [str(value.team_id.id),
                                    value.team_id.name] if value.team_id else [],
                        'measure_on': value.measure_on if value.measure_on else "",
                        'lot_id': value.lot_id if value.lot_id else "",
                        'control_date': value.control_date if value.control_date else "",
                        'quality_state': dict(value._fields['quality_state'].selection).get(
                            value.quality_state) if value.quality_state else ""

                    })

            rec[
                'quality_check_todo'] = stock_picking_obj.quality_check_todo if stock_picking_obj.quality_check_todo else False
            rec[
                'quality_check_fail'] = stock_picking_obj.quality_check_fail if stock_picking_obj.quality_check_fail else False

        return res

    @staticmethod
    def post_picking_validate_response_data(req_params):

        response = []
        req_data = req_params if len(req_params) > 0 else json.loads(
            request.httprequest.data.decode())  # convert the bytes format to dict format

        if req_data.get('quality_check', False):
            response += BistaQualityApi.post_quality_state_quality_data(req_data)

        res = super(BistaWmsApiInherit, BistaWmsApiInherit).post_picking_validate_response_data(req_data)
        response.append(res)

        return response

    @staticmethod
    def get_batch_detail_response_data(self, stock_picking_batch_objs, response_data):

        res = super().get_batch_detail_response_data(self, stock_picking_batch_objs, response_data)

        for rec in res:

            stock_picking_batch_obj = stock_picking_batch_objs.filtered(lambda q: q.id == rec['id'])

            rec[
                'batch_quality_check_todo'] = stock_picking_batch_obj.quality_check_todo if stock_picking_batch_obj.quality_check_todo else False
            rec['quality_check'] = []

            if rec['batch_quality_check_todo']:
                for value in stock_picking_batch_obj.picking_ids:

                    check_ids = []
                    for quality_check_ids in value.check_ids:
                        check_ids.append({
                            'id': quality_check_ids.id if quality_check_ids.id else "",
                            'name': quality_check_ids.name if quality_check_ids.name else "",
                            'user_id': [str(quality_check_ids.user_id.id),
                                        quality_check_ids.user_id.name] if quality_check_ids.user_id else [],
                            'product_id': [str(quality_check_ids.product_id.id),
                                           quality_check_ids.product_id.name] if quality_check_ids.product_id else [],
                            'team_id': [str(quality_check_ids.team_id.id),
                                        quality_check_ids.team_id.name] if quality_check_ids.team_id else [],
                            'measure_on': quality_check_ids.measure_on if quality_check_ids.measure_on else "",
                            'lot_id': quality_check_ids.lot_id if quality_check_ids.lot_id else "",
                            'control_date': quality_check_ids.control_date if quality_check_ids.control_date else "",
                            'quality_state': dict(quality_check_ids._fields['quality_state'].selection).get(
                                quality_check_ids.quality_state) if quality_check_ids.quality_state else ""
                        })

                    rec['quality_check'].append({
                        'quality_check_todo': value.quality_check_todo if value.quality_check_todo else False,
                        'quality_check_fail': value.quality_check_fail if value.quality_check_fail else False,
                        'quality_alert_count': value.quality_alert_count if value.quality_alert_count else "",
                        'check_ids': check_ids
                    })

        return res

    @staticmethod
    def post_batch_validate_data(payload):

        response = []
        req_data = payload if len(payload) > 0 else json.loads(
            request.httprequest.data.decode())  # convert the bytes format to dict format

        if req_data.get('quality_check', False):
            response += BistaQualityApi.post_quality_state_quality_data(req_data)

        res = super(BistaWmsApiInherit, BistaWmsApiInherit).post_batch_validate_data(payload)
        response.append(res)

        return response

    # @staticmethod
    # def auth_login_respponse_data(data):

    #     res = super(BistaWmsApiInherit, BistaWmsApiInherit).auth_login_respponse_data(data)

    #     res['status_2'] = False
    #     res['status'] = False

    #     del res['company_id']

    #     return res
