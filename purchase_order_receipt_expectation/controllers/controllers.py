# -*- coding: utf-8 -*-
# from odoo import http


# class PurchaseOrderReceiptExpectation(http.Controller):
#     @http.route('/purchase_order_receipt_expectation/purchase_order_receipt_expectation', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/purchase_order_receipt_expectation/purchase_order_receipt_expectation/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('purchase_order_receipt_expectation.listing', {
#             'root': '/purchase_order_receipt_expectation/purchase_order_receipt_expectation',
#             'objects': http.request.env['purchase_order_receipt_expectation.purchase_order_receipt_expectation'].search([]),
#         })

#     @http.route('/purchase_order_receipt_expectation/purchase_order_receipt_expectation/objects/<model("purchase_order_receipt_expectation.purchase_order_receipt_expectation"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('purchase_order_receipt_expectation.object', {
#             'object': obj
#         })
