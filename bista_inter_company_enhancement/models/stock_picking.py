# -*- encoding: utf-8 -*-
##############################################################################
#
# Bista Solutions Pvt. Ltd
# Copyright (C) 2023 (http://www.bistasolutions.com)
#
##############################################################################

from odoo import models, api, _, fields
from odoo.exceptions import UserError


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    def button_validate(self):
        """
            Inherit for passing additional context to manual PO confirm

            :return:
            @author: Daud Akhtar @Bista Solutions Pvt. Ltd.
        """
        additional_context = {'allow_edit': True}
        # Call the super method with the additional context
        result = super(StockPicking, self.with_context(additional_context)).button_validate()
        # You can now use the result or perform any additional actions
        return result

    @api.depends('purchase_id')
    def compute_inter_ref(self):
        """
            For restriction: Added a boolean for inter-company record

            :return:
            @author: Daud Akhtar @Bista Solutions Pvt. Ltd.
        """
        for rec in self:
            if rec.purchase_id and rec.purchase_id.bs_inter_so_id:
                rec.bs_is_inter_record = True

    bs_is_inter_record = fields.Boolean(string='Xidax SO Ref', store=True, compute='compute_inter_ref',
                                        default=False)

    # def create(self, vals):
    #     """
    #         INHERIT donot allow duplicate DS and DO for inter-company record
    #
    #         :return:
    #         @author: Daud Akhtar @Bista Solutions Pvt. Ltd.
    #     """
    #     for rec in self:
    #         if rec.bs_is_inter_record:
    #             raise UserError("You cannot duplicate this DS")
    #         # if 'origin' in vals:
    #         #     So_id = self.env['sale.order'].search(
    #         #         [('name', '=', vals.get('origin')), ('bs_inter_so_id', '!=', False)], limit=1)
    #         #     if So_id and So_id.bs_inter_so_id:
    #         #         raise UserError("You cannot duplicate this DO")
    #     res = super(StockPicking, self).create(vals)
    #
    #     return res

    def write(self, vals):
        """
            INHERIT FOR RESTRICT VALUES for inter-company record

            :return:
            @author: Daud Akhtar @Bista Solutions Pvt. Ltd.
        """
        updated_data = dict(self._context)
        for res in self:
            if (
                    res.bs_is_inter_record and res.state != 'cancel' and res.state != 'done' and res.state != 'confirmed' and not updated_data.get(
                    'allow_edit') == True) or (
                    res.bs_is_inter_record and 'allow_edit' not in updated_data and res.state != 'cancel' and res.state != 'done' and res.state != 'confirmed'):
                raise UserError("You cannot change anything from DS. Hints : Cancel SO --> Reset to draft ")
        return super(StockPicking, self).write(vals)

    @api.onchange('move_ids_without_package', 'move_line_ids_without_package', 'move_line_nosuggest_ids')
    def _onchange_move_line(self):
        """
            Added restriction on order line for inter-company record

            :return:
            @author: Daud Akhtar @Bista Solutions Pvt. Ltd.
        """
        if self.move_ids_without_package or self.move_line_ids_without_package or self.move_line_nosuggest_ids:
            updated_data = dict(self._context)
            if (self.bs_is_inter_record and self.state != 'cancel' and not updated_data.get('allow_edit') == True) or (
                    self.bs_is_inter_record and 'allow_edit' not in updated_data and self.state != 'cancel'):
                raise UserError("You cannot change anything from DS Line. Hints : Cancel SO --> Reset to draft ")

    def button_validate(self):
        """
            This function is used to confirm Transfer & then it confirms Receipt of intercompany PO.
            Then creates Invoice for Transfer & post the same. After that creates Vendor Bill of Receipt & post the same.

            :return:
            @author: Daud Akhtar,Ashish Ghadi @Bista Solutions Pvt. Ltd.
        """
        if self._context.get('is_po_picking_validate', []):
            return super(StockPicking, self).with_context({'backorder_bill': True}).button_validate()

        if self._context.get('is_purchase_picking_validate', []):
            res = super(StockPicking, self).with_context({'backorder_bill': True}).button_validate()
        else:
            res = super(StockPicking, self).button_validate()
            for sale_picking in self:
                if sale_picking.picking_type_code == 'outgoing' and sale_picking.sale_id and not sale_picking.picking_type_id.is_subcontractor:
                    sale_order = self.env['sale.order'].search([('name', '=', sale_picking.origin)], limit=1)
                    if sale_order:
                        po_id = self.env["purchase.order"].sudo().browse(sale_order.auto_purchase_order_id.id)
                        if po_id:
                            po_company = po_id.company_id
                            purchase_picking_ids = po_id.picking_ids. \
                                filtered(lambda x: x.state not in ['done', 'cancel'])

                            if purchase_picking_ids:
                                move_line_vals = []
                                for sale_move in sale_picking.move_ids_without_package.filtered(
                                        lambda x: x.quantity_done > 0):
                                    for move_line in sale_move.move_line_ids:
                                        move_line_vals.append({
                                            'product_id': move_line.product_id.id,
                                            'qty_done': move_line.qty_done,
                                            'lot_name': move_line.lot_id.name,
                                            'lot_id': move_line.lot_id.id,
                                            'location_id': move_line.location_id.id,
                                        })

                                for purchase_picking in purchase_picking_ids:
                                    purchase_picking.move_ids_without_package.mapped('move_line_ids').unlink()
                                    company_rec = purchase_picking.mapped('company_id')

                                    po_move_line_vals = []
                                    for move_line_data in move_line_vals:
                                        for purchase_move in purchase_picking.move_ids_without_package. \
                                                filtered(lambda x: x.product_id.id == move_line_data['product_id'] and
                                                                   x.product_uom_qty > x.quantity_done):
                                            lot_id = False

                                            product_in_other_company = self.env['product.product'].sudo().with_company(company_rec).search([('id', '=', self.product_id.id)])
                                            tracking_type = product_in_other_company.tracking

                                            if tracking_type != 'none':
                                                if move_line_data.get('lot_name'):
                                                    lot_id = self.env['stock.lot'].sudo().with_company(company_rec).search(
                                                        [('company_id', '=', company_rec.id),
                                                         ('name', '=', move_line_data['lot_name']),
                                                         ('product_id', '=', move_line_data['product_id'])], limit=1)

                                                    # lot_id = self.env['stock.lot'].sudo().search(
                                                    #     [('name', '=', move_line_data['lot_name']),
                                                    #      ('product_id', '=', move_line_data['product_id'])], limit=1)

                                                    if not lot_id:
                                                        lot_id = self.env['stock.lot'].sudo().with_company(
                                                            company_rec).create({
                                                                'name': move_line_data['lot_name'],
                                                                'product_id': move_line_data['product_id'],
                                                                'company_id': company_rec.id
                                                            })
                                                        # lot_id = self.env['stock.lot'].create({
                                                        #     'name': move_line_data['lot_name'],
                                                        #     'product_id': move_line_data['product_id'],
                                                        #     'company_id': company_rec.id
                                                        # })
                                                        # lot_id = self.env['stock.lot'].sudo().create({
                                                        #     'name': move_line_data['lot_name'],
                                                        #     'product_id': move_line_data['product_id'],
                                                        #     # 'company_id': company_rec.id
                                                        # })
                                                    else:
                                                        move_line_data.update({
                                                            'lot_name': False,
                                                        })
                                            else:
                                                move_line_data.update({
                                                    'lot_name': False,
                                                })

                                            if lot_id:
                                                po_move_line_vals.append({
                                                    'move_id': purchase_move.id,
                                                    'lot_name': lot_id.name,
                                                    'lot_id': lot_id.id,
                                                    'product_id': purchase_move.product_id.id,
                                                    'qty_done': move_line_data.get('qty_done'),
                                                    'company_id': company_rec.id,
                                                    'location_id': purchase_move.location_id.id,
                                                    'location_dest_id': purchase_move.location_dest_id.id,
                                                    'product_uom_id': purchase_move.product_uom.id,
                                                    'picking_id': purchase_move.picking_id.id,
                                                })
                                            else:
                                                po_move_line_vals.append({
                                                    'move_id': purchase_move.id,
                                                    'product_id': purchase_move.product_id.id,
                                                    'qty_done': move_line_data.get('qty_done'),
                                                    'company_id': company_rec.id,
                                                    'location_id': purchase_move.location_id.id,
                                                    'location_dest_id': purchase_move.location_dest_id.id,
                                                    'product_uom_id': purchase_move.product_uom.id,
                                                    'picking_id': purchase_move.picking_id.id,
                                                })
                                    if po_move_line_vals:
                                        intercompany_user = po_company.intercompany_user_id
                                        moves = self.env['stock.move.line'].sudo().with_user(intercompany_user).create(
                                            po_move_line_vals)
                                        shopify_config = self.env['shopify.config'].sudo().with_company(moves.company_id.id).search([('default_company_id', '=', moves.company_id.id)], limit=1)

                                        moves.picking_id.write({
                                            'shipstation_order_id': self.shipstation_order_id,
                                            'shopify_config_id': shopify_config.id})
                                    if purchase_picking.company_id.auto_validate_transfer:
                                        pickings_not_to_backorder = purchase_picking.filtered(
                                            lambda p: p.picking_type_id.create_backorder == 'never')
                                        if self.env.context.get('picking_ids_not_to_backorder'):
                                            pickings_not_to_backorder |= purchase_picking.browse(
                                                self.env.context['picking_ids_not_to_backorder']).filtered(
                                                lambda p: p.picking_type_id.create_backorder != 'always'
                                            )
                                        pickings_to_backorder = purchase_picking - pickings_not_to_backorder

                                        if pickings_to_backorder:
                                            for po_pickings_to_backorder in pickings_to_backorder:
                                                po_pickings_to_backorder.button_validate()
                                        else:
                                            purchase_picking.write({
                                                'shipstation_order_id': self.shipstation_order_id,
                                                'shopify_config_id': shopify_config.id})
                                            purchase_picking.with_context(
                                                {'is_po_picking_validate': True}).button_validate()

                if sale_picking.picking_type_id.code == 'outgoing':
                    sale_order = sale_picking.move_ids_without_package.mapped('sale_line_id').order_id
                    sale_order.with_context({'allow_edit': True})._compute_invoice_status()
                    # if sale_order.invoice_status == 'to invoice':
                    #     invoice_id = sale_order._create_invoices(final=True)
                    #     invoice_id.filtered(lambda x: x.state == 'draft').sudo().action_post()
                    #     # ----------------
                    #
                    #     store_po = sale_order.sudo().auto_purchase_order_id.name
                    #     bill_id = self.env["account.move"].sudo().search(
                    #         [('ref', '=', store_po), ('state', '=', 'draft'),
                    #          ('move_type', '=', 'in_invoice')], limit=1)
                    #     bill_id.sudo().button_cancel()
                    #     bill_id.sudo().unlink()
                    #     # --------------------
                    #
                    po_id = self.env["purchase.order"].sudo().browse(sale_order.auto_purchase_order_id.id)
                    po_id.with_context({'allow_edit': True})._get_invoiced()

                    if po_id.invoice_status == 'to invoice':
                        vendor_bill_id = po_id.action_create_invoice()
                        vendor_bill = self.env['account.move'].sudo().browse(vendor_bill_id.get('res_id'))
                        invoice_id = po_id.invoice_ids
                        if vendor_bill:
                            if self.company_id and self.company_id.bs_neg_prod_id:
                                # ---------added for move and config product---------#
                                bill_acc_move_id = self.env['account.move.line'].sudo().create({
                                    'product_id': self.company_id.bs_neg_prod_id.id or False,
                                    'quantity': -1,
                                    'move_id': vendor_bill.id or False,
                                    'tax_ids': False,
                                    'price_unit': vendor_bill.amount_total or 0.0
                                })
                                acc_move_id = self.env['account.move.line'].sudo().create({
                                    'product_id': self.company_id.bs_neg_prod_id.id or False,
                                    'quantity': -1,
                                    'tax_ids': False,
                                    'move_id': invoice_id.id or False,
                                    'price_unit': invoice_id.amount_total or 0.0
                                })
                                # ---------added for move and config product---------#
                                vendor_bill.sudo().update({
                                    'auto_invoice_id': invoice_id,
                                    'invoice_date': invoice_id.invoice_date,
                                    'invoice_line_ids': [(4, 0, bill_acc_move_id)]
                                })
                                invoice_id.sudo().update({
                                    'invoice_line_ids': [(4, 0, acc_move_id)]
                                })
                            else:
                                vendor_bill.sudo().update({
                                    'auto_invoice_id': invoice_id,
                                    'invoice_date': invoice_id.invoice_date,
                                })
                            if po_id.company_id.auto_validate_vendor_bill:
                                vendor_bill.sudo().action_post()

        return res
