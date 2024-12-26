# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from datetime import datetime
from odoo.exceptions import UserError, ValidationError


class PurchaseOrderWizard(models.TransientModel):
    _name = 'purchase.order.wizard'
    _description = "Purchase Order Wizard"

    partner_id = fields.Many2one('res.partner', string='Vendor', required=True)
    order_line = fields.One2many(
        'purchase.order.line.wizard', 'wizard_id', string='Order Lines')
    date_planned = fields.Datetime(
        string='Scheduled Date', required=True, default=datetime.now())
    order_selection = fields.Selection(
        [('rfq', 'RFQ'), ('order', 'Purchase Order')], default='order', required=True)
    purchase_type = fields.Selection([
        ('dropship', 'Dropship')
        ],
        string="Purchase Type", default='dropship')
    company_id = fields.Many2one('res.company', required=True, readonly=True, default=lambda self: self.env.company)

        
    def sh_create_dropship_order(self):
        purchase_order_line_obj = self.env['purchase.order.line']
        purchase_order_obj = self.env['purchase.order']
        picking_type_obj = self.env['stock.picking.type']
        active_so_id = self.env.context.get("active_id")
        sale_order_search = self.env['sale.order'].sudo().browse(active_so_id)
        if self and self.partner_id and self.date_planned and active_so_id:
            company = self.company_id.dropship_company_id
            if not company:
                raise ValidationError("Please set Dropship company in company configuration.")
            picking_type_id = picking_type_obj.sudo().search([('name', 'ilike', 'Dropship'),
                                                       ('sequence_code', 'ilike', 'DS'),
                                                       ('company_id', '=', company.id)], limit=1)
            vals = {'partner_id': self.partner_id.id,
                    'date_planned': self.date_planned,
                    'sh_sale_order_id': active_so_id,
                    'picking_type_id': picking_type_id.id,
                    'type_of_purchase': "dropship",
                    'dest_address_id': self.env.context.get("partner_shipping_id"),
                    'notes': "This drop-shipping order is created from sale order "+str(sale_order_search.name)
                    }
            created_po = False
            if self.order_line:
                created_po = purchase_order_obj.with_company(company).create(vals)
            if created_po and self.order_line:
                tax = []
                for ol in self.order_line:
                    if ol.product_id and ol.name and ol.product_id.uom_po_id and not ol.product_id.type == 'service':
                        purchase_line = purchase_order_line_obj.with_company(company).create({'product_id': ol.product_id.id,
                                                        'name': ol.name,
                                                        'product_uom': ol.product_id.uom_id.id,
                                                        'order_id': created_po.id,
                                                        # 'date_planned': self.date_planned,
                                                        'product_qty': ol.product_qty,
                                                        'price_unit': ol.price_unit,
                                                        'taxes_id': [(6, 0, tax)],
                                                        'sale_line_id': ol.so_line_id.id if self.purchase_type == "dropship" else False,
                                                        })
                        if purchase_line and ol.so_line_id:
                            for each_rec in sale_order_search.picking_ids.filtered(lambda r: r.state != 'done'):
                                lines_to_delete = each_rec.move_ids_without_package.filtered(
                                    lambda rec: rec.product_id.id == purchase_line.product_id.id)
                                if lines_to_delete:
                                    lines_to_delete.write({'state': 'draft'})
                                    lines_to_delete.unlink()
                            ol.so_line_id.sudo().write({'is_dropship': True})

                if self.order_selection == 'order':
                    created_po.button_confirm()
                purchase_order_ref = """<a href=# data-oe-model=purchase.order 
                                                    data-oe-id=%s>%s</a>""" % (created_po.id, created_po.name)
                sale_order_search.sudo().message_post(
                    body='Dropship order has been created for this sale order as %s' % purchase_order_ref)
                if self.company_id == created_po.company_id or created_po.company_id.id in self.env.companies.ids:
                    return {
                        "type": "ir.actions.act_window",
                        "res_model": "purchase.order",
                        "views": [[False, "form"]],
                        "res_id": created_po.id,
                        "target": "self",
                    }
                else:
                    message = _("Dropship created in company - %s", created_po.company_id.name)
                    return {
                        'type': 'ir.actions.client',
                        'tag': 'display_notification',
                        'params': {
                                      'message': message,
                                      'type': 'success',
                                      'sticky': False,
                                  }
                    }


    @api.model
    def default_get(self, fields):
        res = super(PurchaseOrderWizard, self).default_get(fields)
        active_so_id = self.env.context.get("active_id")
        sale_order_obj = self.env['sale.order']
        if active_so_id:
            sale_order_search = sale_order_obj.browse(active_so_id)
            if sale_order_search and sale_order_search.order_line:
                tick_order_line = []
                for rec in sale_order_search.order_line:
                    if rec.tick and rec.product_uom_qty != rec.qty_delivered:
                        tick_order_line.append(rec.id)
                if len(tick_order_line) > 0:
                    result = []
                    for rec in sale_order_search.order_line.search([('id', 'in', tick_order_line)]).filtered(lambda line: line.product_id.type != 'service'):
                        name = rec.product_id.name_get()[0][1] if rec.product_id else ''
                        price = rec.product_id.standard_price
                        if not rec.check_existing_stock_moves():
                            result.append((0, 0, {'product_id': rec.product_id.id,
                                                  'name': name,
                                                  'product_qty': rec.product_uom_qty - rec.qty_delivered,
                                                  'price_unit': price,
                                                  'product_uom': rec.product_uom.id,
                                                  'price_subtotal': rec.product_id.standard_price * rec.product_uom_qty,
                                                  'so_line_id': rec.id
                                                  }))
                    res.update({'order_line': result})
                elif len(tick_order_line) == 0:
                    result = []
                    for rec in sale_order_search.order_line.filtered(lambda line:
                                                                     line.product_uom_qty != line.qty_delivered
                                                                     and not line.product_id.type == 'service'
                                                                     and 'done' not in line.move_ids.mapped('state')
                                                                     and not line.is_dropship):
                        name = rec.product_id.name_get()[0][1]
                        price = rec.product_id.standard_price
                        if not rec.check_existing_stock_moves():
                            result.append((0, 0, {'product_id': rec.product_id.id,
                                                  'name': name,
                                                  'product_qty': rec.product_uom_qty - rec.qty_delivered,
                                                  'price_unit': price,
                                                  'product_uom': rec.product_uom.id,
                                                  'price_subtotal': rec.product_id.standard_price * rec.product_uom_qty,
                                                  'so_line_id': rec.id
                                                  }))
                    res.update({'order_line': result})
        return res