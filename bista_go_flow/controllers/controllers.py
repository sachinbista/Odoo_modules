# -*- coding: utf-8 -*-
# from odoo import http


# class BistaGoFlow(http.Controller):
#     @http.route('/bista_go_flow/bista_go_flow', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/bista_go_flow/bista_go_flow/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('bista_go_flow.listing', {
#             'root': '/bista_go_flow/bista_go_flow',
#             'objects': http.request.env['bista_go_flow.bista_go_flow'].search([]),
#         })

#     @http.route('/bista_go_flow/bista_go_flow/objects/<model("bista_go_flow.bista_go_flow"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('bista_go_flow.object', {
#             'object': obj
#         })
