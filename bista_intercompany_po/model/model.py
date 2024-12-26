from docutils.nodes import warning

from odoo import models, api,fields,_
from odoo.exceptions import UserError, ValidationError


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    parent_company_id = fields.Many2one('res.company', string='Parent Company')
    parent_purchase_order_id = fields.Many2one('purchase.order', string='Parent Purchase Order')
    inter_company_vendor_id = fields.Many2one('res.partner',string='Inter-company Vendor')
    internal_order_ref = fields.Char(string="Order Reference/Owner's reference",copy=False)

    @api.constrains('internal_order_ref')
    def _check_unique_internal_order_ref(self):
        for record in self:
            if record.internal_order_ref:
                existing_records = self.search([
                    ('internal_order_ref', '=', record.internal_order_ref),
                    ('company_id', '=', record.company_id.id),
                    ('id', '!=', record.id)
                ])
                if existing_records:
                    raise ValidationError("The Order Reference/Owner's reference must be unique.")

    def _prepare_picking(self):
        res = super(PurchaseOrder, self)._prepare_picking()
        res.update({
            'internal_order_ref': self.internal_order_ref,
        })
        return res

    def _prepare_invoice(self):
        invoice_vals = super(PurchaseOrder, self)._prepare_invoice()
        invoice_vals.update({
            'internal_order_ref': self.internal_order_ref,
        })
        return invoice_vals

    def button_confirm(self):
        res = super(PurchaseOrder, self).button_confirm()

        if self.company_id.is_inter_company == True and self.company_id.first_company_id.partner_id == self.partner_id:

            if self.company_id.secound_company_id or self.company_id.first_company_id:
                company_ids = self.company_id.secound_company_id + self.company_id.first_company_id

                for order in self:
                    if not order.company_id:
                        continue
                    for company_id in company_ids:
                        company = company_id
                        order.with_user(company.intercompany_user_id).with_context(default_company_id=company.id).with_company(company).inter_custom_company_create_purchase_order(company)
            return res

    def button_approve(self, force=False):
        self = self.filtered(lambda order: order._approval_allowed())
        self.write({'state': 'purchase', 'date_approve': fields.Datetime.now()})
        self.filtered(lambda p: p.company_id.po_lock == 'lock').write({'state': 'done'})
        self._create_picking()
        return {}

    def inter_custom_company_create_purchase_order(self, company):
        for rec in self:
            if not company or not rec.company_id.partner_id:
                continue
            intercompany_uid = company.intercompany_user_id and company.intercompany_user_id.id or False
            if not intercompany_uid:
                raise UserError(_('Provide one user for intercompany relation for %(name)s '), name=company.name)
            if not self.env['purchase.order'].with_user(intercompany_uid).check_access_rights('create', raise_exception=False):
                raise UserError(_("Inter company user of company %s doesn't have enough access rights", company.name))
            company_partner = rec.company_id.partner_id.with_user(intercompany_uid)
            po_vals = rec.sudo()._prepare_custom_purchase_order_data(company)
            for line in rec.order_line.sudo():
                po_vals['order_line'] += [(0, 0, rec._prepare_custom_purchase_order_line_data(line,company))]
            po_vals.update({'parent_company_id': rec.company_id.id})
            if self.company_id.first_company_id:
                po_vals.update({'parent_purchase_order_id': rec.id})
            purchase_order = self.env['purchase.order'].create(po_vals)
            purchase_order.button_confirm()
            rec.origin = purchase_order.name

    def _prepare_custom_purchase_order_data(self,company):

        if company == self.company_id.first_company_id:
            company_partner = self.company_id.secound_company_id.partner_id

        if company == self.company_id.secound_company_id:
            # partner_default = self.env['res.partner'].search([('default_partner','=',True)])
            company_partner = self.inter_company_vendor_id


        self.ensure_one()
        warehouse = company.warehouse_id
        if not warehouse:
            raise UserError(_('Configure correct warehouse for company(%s) from Menu: Settings/Users/Companies', company.name))
        picking_type_id = self.env['stock.picking.type'].search([
            ('code', '=', 'incoming'), ('warehouse_id', '=', warehouse.id)
        ], limit=1)
        if not picking_type_id:
            picking_type_id = self.env['purchase.order'].with_user(company)._default_picking_type()
        return {
            'name': self.name,
            'origin': self.name,
            'partner_id': company_partner.id,
            'picking_type_id': picking_type_id.id,
            'internal_order_ref': self.internal_order_ref,
            'date_order': self.date_order,
            'company_id': company.id,
            'fiscal_position_id': company_partner.property_account_position_id.id,
            'payment_term_id': company_partner.property_supplier_payment_term_id.id,
            'auto_generated': True,
            'partner_ref': self.name,
            'currency_id': self.currency_id.id,
            'order_line': [],
            'inter_company_vendor_id':self.inter_company_vendor_id.id
        }

    @api.model
    def _prepare_custom_purchase_order_line_data(self, line, company):
        price = line.price_unit - (line.price_unit * (line.discount / 100))
        quantity = line.product_id and line.product_uom._compute_quantity(line.product_uom_qty,
                                                                                line.product_id.uom_po_id) or line.product_uom_qty
        price = line.product_id and line.product_uom._compute_price(price, line.product_id.uom_po_id) or price
        return {
            'name': line.name,
            'product_qty': quantity,
            'product_id': line.product_id and line.product_id.id or False,
            'product_uom': line.product_id and line.product_id.uom_po_id.id or line.product_uom.id,
            'price_unit': price or 0.0,
            'company_id': company.id,
            'date_planned': line.order_id.date_order,
            'display_type': line.display_type,
        }

    def _prepare_customer_invoice(self,parent_company_id):
        self.ensure_one()
        move_type = self._context.get('default_move_type', 'out_invoice')
        partner_id = self.env['res.partner']
        if self.company_id == parent_company_id.secound_company_id:
            partner_id = parent_company_id.first_company_id.partner_id
        if self.company_id == parent_company_id.first_company_id:
            partner_id = parent_company_id.partner_id
        partner_invoice = self.env['res.partner'].browse(partner_id.address_get(['invoice'])['invoice'])
        partner_bank_id = partner_id.commercial_partner_id.bank_ids.filtered_domain(
            ['|', ('company_id', '=', False), ('company_id', '=', self.company_id.id)])[:1]

        invoice_vals = {
            'ref': self.partner_ref or '',
            'move_type': move_type,
            'narration': self.notes,
            'currency_id': self.currency_id.id,
            'partner_id': partner_invoice.id,
            'internal_order_ref': self.internal_order_ref,
            'fiscal_position_id': (
                        self.fiscal_position_id or self.fiscal_position_id._get_fiscal_position(partner_invoice)).id,
            'payment_reference': self.partner_ref or '',
            'partner_bank_id': partner_bank_id.id,
            'invoice_origin': self.name,
            'invoice_payment_term_id': self.payment_term_id.id,
            'invoice_line_ids': [],
            'company_id': self.company_id.id,
        }
        return invoice_vals




