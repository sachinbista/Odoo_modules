# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError, RedirectWarning, ValidationError, Warning
import copy


class PurchaseOrderMerge(models.TransientModel):
    _name = 'purchase.order.merge'
    _description = 'Merge Purchase orders'

    purchase_order = fields.Many2one(
        'purchase.order', 'Merge into')
    purchase_order_to_merge = fields.Many2many(
        'purchase.order', 'rel_purchase_to_merge', 'purchase_id', 'to_merge_id',
        'Orders to merge')
    type = fields.Selection(
        [('new', 'New Order and Cancel Selected'), ('exist', 'New order and Delete all selected order'),
         ('exist_1', 'Merge order on existing selected order and cancel others'),
         ('exist_2', 'Merge order on existing selected order and delete others')], 'Merge Type', default='new',
        required=True)
    merge_with_diff_partner = fields.Boolean(
        string='Merge with Different Partner')
    partner_id = fields.Many2one(
        'res.partner', 'Vendor')

    @api.model
    def default_get(self, fields):
        rec = super(PurchaseOrderMerge, self).default_get(fields)
        context = dict(self._context or {})
        active_model = context.get('active_model')
        active_ids = context.get('active_ids')

        if active_ids:
            purchase_ids = []
            purchases = self.env['purchase.order'].browse(active_ids)

            if any(pur.state == 'done' for pur in purchases):
                raise UserError('You can not merge done orders.')

            purchase_ids = [pur.id for pur in purchases]

            if 'purchase_order_to_merge' in fields:
                rec.update({'purchase_order_to_merge': [(6, 0, purchase_ids)]})
        return rec

    @api.onchange('merge_with_diff_partner')
    def set_data(self):
        if self.merge_with_diff_partner:
            self.purchase_order = False
            self.type = 'new'
        elif not self.merge_with_diff_partner:
            self.partner_id = False


    def merge_purchase(self):
        purchase_obj = self.env['purchase.order']
        mod_obj = self.env['ir.model.data']
        line_obj = self.env['purchase.order.line']
        purchases = purchase_obj.browse(self._context.get('active_ids', []))
        partners_list = []
        partners_list_write = []
        line_list = []
        cancel_list = []
        copy_list = []
        vendor_ref = []
        myString = ''
        new_purchase = False
        if len(purchases) < 2:
            raise UserError('Please select multiple orders to merge in the list view.')

        if any(pur.state in ['done', 'purchase', 'cancel'] for pur in purchases):
            raise UserError('You can not merge this order with existing state.')
        for pur in purchases:
            if pur.partner_ref:
                vendor_ref.append(pur.partner_ref)
                if len(vendor_ref) > 1:
                    myString = ",".join(vendor_ref)
                else:
                    myString = vendor_ref[0]

        msg_origin = ""
        origin_list = []


        for pur in purchases:
            origin_list.append(pur.name)
        if self.purchase_order:
            origin_list.append(self.purchase_order.name)

        if len(origin_list) == 1:
            msg_origin = msg_origin + origin_list[0] + "."
        elif len(origin_list) > 1:
            msg_origin = ', '.join(set(origin_list))

        if not self.merge_with_diff_partner:
            if self.purchase_order:
                self.purchase_order.write({'partner_ref': myString})
            if self.type == 'new':
                with_section = []
                without_section = []
                partner_name = purchases and purchases[0].partner_id.id
                new_purchase = purchase_obj.create(
                    {'partner_id': partner_name, 'partner_ref': myString or '', 'state': 'draft', 'origin': msg_origin})
                for pur in purchases:
                    partners_list.append(pur.partner_id)

                    if not partners_list[1:] == partners_list[:-1]:
                        raise UserError('You can only merge orders of same partners.')

                    else:
                        cancel_list.append(pur)
                        merge_ids = line_obj.search([('order_id', '=', pur.id)])
                        for line in merge_ids:
                            if line.display_type == 'line_section':
                                section_vals = {
                                    'display_type': 'line_section',
                                    'name': line.name,
                                    'order_id': new_purchase.id,
                                    'product_qty': 0.0 or False,
                                    'product_uom': '' or False,
                                }
                                with_section.append((0, 0, section_vals))
                            else:
                                vals = {
                                    'date_planned': line.date_planned or False,
                                    'name': line.product_id.name or False,
                                    'product_id': line.product_id.id or False,
                                    'product_qty': line.product_qty or False,
                                    'product_uom': line.product_uom.id or False,
                                    'price_unit': line.price_unit or False,
                                    'taxes_id': [(6, 0, [tax.id for tax in line.taxes_id if line.taxes_id])] or False,
                                    'order_id': new_purchase.id,
                                }
                                # line_obj.create(vals)
                                without_section.append((0, 0, vals))
                lines = with_section + without_section
                final_view_id=new_purchase.id
                msg_body = _("This purchases order has been created from: <b>%s</b>") % (msg_origin)
                new_purchase.message_post(body=msg_body)
                new_purchase.write({'partner_id': partner_name,
                                    'order_line': lines})

                for orders in cancel_list:
                    orders.button_cancel()
            if self.type == 'exist':
                with_section = []
                without_section = []
                partner_name = purchases and purchases[0].partner_id.id
                new_purchase = purchase_obj.create({
                    'partner_id': partner_name,
                    'partner_ref': myString or '',
                    'state': 'draft',
                    'origin': msg_origin})
                for pur in purchases:
                    partners_list_write.append(pur.partner_id)

                    if not partners_list_write[1:] == partners_list_write[:-1]:
                        raise UserError('You can only merge orders of same partners.')

                    else:
                        partner_name = pur.partner_id.id
                        cancel_list.append(pur)
                        merge_ids = line_obj.search([('order_id', '=', pur.id)])
                        for line in merge_ids:
                            if line.display_type == 'line_section':
                                section_vals = {
                                    'display_type': 'line_section',
                                    'name': line.name,
                                    'order_id': new_purchase.id,
                                    'product_qty': 0.0 or False,
                                    'product_uom': '' or False,
                                }
                                with_section.append((0, 0, section_vals))
                            else:
                                vals = {
                                    'date_planned': line.date_planned or False,
                                    'name': line.product_id.name or False,
                                    'product_id': line.product_id.id or False,
                                    'product_qty': line.product_qty or False,
                                    'product_uom': line.product_uom.id or False,
                                    'price_unit': line.price_unit or False,
                                    'taxes_id': [(6, 0, [tax.id for tax in line.taxes_id if line.taxes_id])] or False,
                                    'order_id': new_purchase.id,
                                }
                                # line_obj.create(vals)
                                without_section.append((0, 0, vals))
                lines = with_section + without_section
                final_view_id=new_purchase.id
                msg_body = _("This purchases order has been created from: <b>%s</b>") % (msg_origin)
                new_purchase.message_post(body=msg_body)
                new_purchase.write({'partner_id': partner_name,
                                    'order_line': lines})

                for orders in cancel_list:
                    orders.button_cancel()
                for orders in cancel_list:
                    orders.unlink()

            if self.type == 'exist_1':
                for pur in purchases:
                    partners_list_write.append(pur.partner_id)
                    partners_list_write.append(self.purchase_order.partner_id)
                    cancel_list.append(pur.id)

                    user = partners_list_write
                    set1 = set(partners_list_write)
                    if len(set1) > 1:
                        raise UserError('You can only merge orders of same partners.')
                    else:
                        partner_name = pur.partner_id.id
                        merge_ids = line_obj.search([('order_id', '=', pur.id)])
                        for line in merge_ids:
                            line.write({'order_id': self.purchase_order.id})

                final_view_id=self.purchase_order.id
                msg_body = _("This purchases order has been created from: <b>%s</b>") % (msg_origin)
                self.purchase_order.message_post(body=msg_body)
                self.purchase_order.write({
                    'partner_id': partner_name,
                    'origin': msg_origin})

                if self.purchase_order.id in cancel_list:
                    cancel_list.remove(self.purchase_order.id)
                for orders in cancel_list:
                    for s_order in self.env['purchase.order'].browse(orders):
                        s_order.button_cancel()
                return True

            if self.type == 'exist_2':
                for pur in purchases:
                    partners_list_write.append(pur.partner_id)
                    partners_list_write.append(self.purchase_order.partner_id)
                    cancel_list.append(pur.id)

                    user = partners_list_write
                    set1 = set(partners_list_write)
                    if len(set1) > 1:
                        raise UserError('You can only merge orders of same partners.')
                    else:
                        partner_name = pur.partner_id.id
                        merge_ids = line_obj.search([('order_id', '=', pur.id)])
                        for line in merge_ids:
                            if self.purchase_order.state in ['done', 'purchase', 'to approve', 'cancel']:
                                raise UserError('You can not merge oredrs with Done, Cancel and Purchase order orders.')
                            else:
                                line.write({'order_id': self.purchase_order.id})
                final_view_id=self.purchase_order.id
                msg_body = _("This purchases order has been created from: <b>%s</b>") % (msg_origin)
                self.purchase_order.message_post(body=msg_body)
                self.purchase_order.write({
                    'partner_id': partner_name,
                    'origin': msg_origin})

                if self.purchase_order.id in cancel_list:
                    cancel_list.remove(self.purchase_order.id)
                for orders in cancel_list:
                    p_order = self.env['purchase.order'].browse(orders)
                    p_order.button_cancel()
                    p_order.unlink()

        else:
            partner_name = self.partner_id.id
            new_purchase = purchase_obj.create({
                'partner_id': partner_name,
                'partner_ref': myString or '',
                'state': 'draft',
                'origin': msg_origin})
            for pur in purchases:
                partners_list.append(pur.partner_id)
                cancel_list.append(pur)
                merge_ids = line_obj.search([('order_id', '=', pur.id)])
                for line in merge_ids:
                    vals = {
                        'date_planned': line.date_planned or False,
                        'name': line.product_id.name or False,
                        'product_id': line.product_id.id or False,
                        'product_qty': line.product_qty or False,
                        'product_uom': line.product_uom.id or False,
                        'price_unit': line.price_unit or False,
                        'taxes_id': [(6, 0, [tax.id for tax in line.taxes_id if line.taxes_id])] or False,
                        'order_id': new_purchase.id,
                    }
                    line_obj.create(vals)
            final_view_id=new_purchase.id
            msg_body = _("This purchases order has been created from: <b>%s</b>") % (msg_origin)
            new_purchase.message_post(body=msg_body)
            new_purchase.write({'partner_id': partner_name})

            for orders in cancel_list:
                orders.button_cancel()

        result = {
            'type': 'ir.actions.act_window',
            'res_model': 'purchase.order',
            'res_id':final_view_id,
            'view_mode': 'form',
            'view_type': 'form',
            'views': [(False, 'form')],
        }
        return result

