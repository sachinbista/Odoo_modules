# -*- coding: utf-8 -*-
# from odoo import http


# class BistaGoFlowProdcut(http.Controller):
#     @http.route('/bista_go_flow_prodcut/bista_go_flow_prodcut', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/bista_go_flow_prodcut/bista_go_flow_prodcut/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('bista_go_flow_prodcut.listing', {
#             'root': '/bista_go_flow_prodcut/bista_go_flow_prodcut',
#             'objects': http.request.env['bista_go_flow_prodcut.bista_go_flow_prodcut'].search([]),
#         })

#     @http.route('/bista_go_flow_prodcut/bista_go_flow_prodcut/objects/<model("bista_go_flow_prodcut.bista_go_flow_prodcut"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('bista_go_flow_prodcut.object', {
#             'object': obj
#         })
