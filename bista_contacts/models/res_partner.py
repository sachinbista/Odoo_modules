# -*- encoding: utf-8 -*-

from odoo import models, _, api, fields
from odoo.exceptions import ValidationError, UserError
from datetime import datetime
from uszipcode import SearchEngine

import requests
import re
import logging

_logger = logging.getLogger(__name__)

MONTHS = [
    ('01', 'January'),
    ('02', 'February'),
    ('03', 'March'),
    ('04', 'April'),
    ('05', 'May'),
    ('06', 'June'),
    ('07', 'July'),
    ('08', 'August'),
    ('09', 'September'),
    ('10', 'October'),
    ('11', 'November'),
    ('12', 'December')
]

DAYS = [(str(i), str(i)) for i in range(1, 32)]

current_year = datetime.today().year
YEARS = sorted(
    [(str(current_year - i), str(current_year - i)) for i in range(125) if current_year - i >= 1900]
)


class ResPartnerCommunicationMode(models.Model):
    _name = 'res.partner.communication.mode'
    _description = 'Partner Communication Mode'

    name = fields.Char(string='Name')


class ResPartner(models.Model):
    _inherit = "res.partner"

    relation_partner_id = fields.Many2one('res.partner', 'Relation Partner')
    relation_id = fields.Many2one('res.partner.relation', 'Relation')
    event_dates_ids = fields.One2many(
        'res.partner.event.dates',
        'partner_id',
        string='Event Dates', context={'active_test': False})
    no_marketing = fields.Boolean('Opt-out Marketing')
    card_completion_per = fields.Float(
        string='Card Completion Percent',
        compute='compute_card_completion_percent', compute_sudo=True)
    communication_mode_id = fields.Many2one(
        'res.partner.communication.mode', string='Preferred Mode of Communication')
    notification_method = fields.Selection([
        ('SMS', 'SMS'),
        ('Email', 'Email')
    ], string='Preferred Mode of Notification')
    birth_month = fields.Selection(MONTHS, string='Birth Month')
    birth_day = fields.Selection(DAYS, string='Birth Day')
    birth_year = fields.Selection(YEARS, string='Birth Year')
    child_all_count = fields.Integer(
        'Indirect Surbordinates Count',
        compute='_compute_subordinates', store=False,
        compute_sudo=True, recursive=True)
    subordinate_ids = fields.One2many(
        'res.partner', 'parent_id', string='Subordinates',
        domain=[('active', '=', True)],
        compute_sudo=True, compute='_compute_subordinates')
    street = fields.Char(tracking=True)
    street2 = fields.Char(tracking=True)
    zip = fields.Char(tracking=True)
    city = fields.Char(tracking=True)
    state_id = fields.Many2one(tracking=True)
    country_id = fields.Many2one(tracking=True)
    purchase_order_amount = fields.Float(
        compute='_compute_purchase_amount',
        string='Purchase Order Amount')
    sale_order_amount = fields.Float(
        compute='_compute_sale_amount',
        string='Sale Order Amount')
    vendor_bill_amount = fields.Float(
        compute='_compute_vendor_bill_amount',
        string='Vendor Bill Amount')
    crm_amount = fields.Float(
        compute='_compute_crm_amount',
        string='CRM Amount')
    pos_order_amount = fields.Float(
        compute='_compute_pos_order_amount',
        string='POS Order Amount')
    card_completion_percent = fields.Float('Card Completion %')
    birth_date = fields.Date('Birthdate')

    def _compute_pos_order(self):
        # retrieve all children partners and prefetch 'parent_id' on them
        all_partners = self.with_context(active_test=False).search([('id', 'child_of', self.ids)])
        all_partners.read(['parent_id'])

        pos_order_data = self.env['pos.order']._read_group(
            domain=[('partner_id', 'in', all_partners.ids),
                    ('state', '!=', 'cancel')],
            fields=['partner_id'], groupby=['partner_id']
        )

        self.pos_order_count = 0
        for group in pos_order_data:
            partner = self.browse(group['partner_id'][0])
            while partner:
                if partner in self:
                    partner.pos_order_count += group['partner_id_count']
                partner = partner.parent_id

    def action_view_pos_order(self):
        action = super(ResPartner, self).action_view_pos_order()
        action["domain"] += [('state', '!=', 'cancel')]
        return action

    def action_view_sale_order(self):
        action = super(ResPartner, self).action_view_sale_order()
        action["domain"] += [('state', '!=', 'cancel')]
        return action

    @api.model
    def _get_sale_order_domain_count(self):
        sale_count_domain = super(ResPartner, self)._get_sale_order_domain_count()
        sale_count_domain.append(('state', '!=', 'cancel'))
        return sale_count_domain

    def _compute_purchase_order_count(self):
        # retrieve all children partners and prefetch 'parent_id' on them
        all_partners = self.with_context(active_test=False).search([('id', 'child_of', self.ids)])
        all_partners.read(['parent_id'])

        purchase_order_groups = self.env['purchase.order']._read_group(
            domain=[('partner_id', 'in', all_partners.ids),
                    ('state', '!=', 'cancel')],
            fields=['partner_id'], groupby=['partner_id']
        )
        partners = self.browse()
        for group in purchase_order_groups:
            partner = self.browse(group['partner_id'][0])
            while partner:
                if partner in self:
                    partner.purchase_order_count += group['partner_id_count']
                    partners |= partner
                partner = partner.parent_id
        (self - partners).purchase_order_count = 0

    def _compute_supplier_invoice_count(self):
        # retrieve all children partners and prefetch 'parent_id' on them
        all_partners = self.with_context(active_test=False).search([('id', 'child_of', self.ids)])
        all_partners.read(['parent_id'])

        supplier_invoice_groups = self.env['account.move']._read_group(
            domain=[('partner_id', 'in', all_partners.ids),
                    ('move_type', 'in', ('in_invoice', 'in_refund')),
                    ('state', '!=', 'cancel')],
            fields=['partner_id'], groupby=['partner_id']
        )
        partners = self.browse()
        for group in supplier_invoice_groups:
            partner = self.browse(group['partner_id'][0])
            while partner:
                if partner in self:
                    partner.supplier_invoice_count += group['partner_id_count']
                    partners |= partner
                partner = partner.parent_id
        (self - partners).supplier_invoice_count = 0

    def get_all_partners(self):
        for record in self:
            all_partners = self.with_context(active_test=False).search(
                [('id', 'child_of', record.ids)])
            return all_partners

    def _compute_sale_amount(self):
        for record in self:
            sale_order_amount = 0
            all_partners = record.get_all_partners()
            sale_order_ids = self.env['sale.order'].search(
                [('partner_id', 'in', all_partners.ids),
                 ('state', '!=', 'cancel')])
            if sale_order_ids:
                sale_order_amount = sum(sale_order_ids.mapped('amount_total'))
            record.write({
                'sale_order_amount': sale_order_amount
            })

    def _compute_purchase_amount(self):
        for record in self:
            purchase_order_amount = 0
            all_partners = record.get_all_partners()
            purchase_order_ids = self.env['purchase.order'].search(
                [('partner_id', 'in', all_partners.ids),
                 ('state', '!=', 'cancel')])
            if purchase_order_ids:
                purchase_order_amount = sum(purchase_order_ids.mapped('amount_total'))
            record.write({
                'purchase_order_amount': purchase_order_amount
            })

    def _compute_vendor_bill_amount(self):
        for record in self:
            vendor_bill_amount = 0
            all_partners = record.get_all_partners()
            vendor_bill_ids = self.env['account.move'].search(
                [('partner_id', 'in', all_partners.ids),
                 ('state', '!=', 'cancel'),
                 ('move_type', 'in', ('in_invoice', 'in_refund'))])
            if vendor_bill_ids:
                vendor_bill_amount = sum(vendor_bill_ids.mapped('amount_total'))
            record.write({
                'vendor_bill_amount': vendor_bill_amount
            })

    def _compute_pos_order_amount(self):
        for record in self:
            pos_order_amount = 0
            all_partners = record.get_all_partners()
            pos_order_ids = self.env['pos.order'].search(
                [('partner_id', 'in', all_partners.ids),
                 ('state', '!=', 'cancel')])
            if pos_order_ids:
                pos_order_amount = sum(pos_order_ids.mapped('amount_total'))
            record.write({
                'pos_order_amount': pos_order_amount
            })

    def _compute_crm_amount(self):
        for record in self:
            crm_amount = 0
            all_partners = record.get_all_partners()
            crm_ids = self.env['crm.lead'].search(
                [('partner_id', 'in', all_partners.ids)])
            if crm_ids:
                crm_amount = sum(crm_ids.mapped('expected_revenue'))
            record.write({
                'crm_amount': crm_amount
            })

    def _get_relation_partner_values(self, relation_partner_id=False):
        values = {}
        if relation_partner_id:
            values.update({
                'name': relation_partner_id.name,
                'firstname': relation_partner_id.firstname,
                'lastname': relation_partner_id.lastname,
                'email': relation_partner_id.email,
                'mobile': relation_partner_id.mobile,
                'title': relation_partner_id.title,
                'phone': relation_partner_id.phone,
                'street': relation_partner_id.street,
                'street2': relation_partner_id.street2,
                'city': relation_partner_id.city,
                'state_id': relation_partner_id.state_id,
                'country_id': relation_partner_id.country_id,
                'zip': relation_partner_id.zip,
            })
        return values

    @api.onchange('relation_partner_id')
    def onchange_relation_partner_id(self):
        if self.relation_partner_id:
            values = self._get_relation_partner_values(self.relation_partner_id)
            self.write(values)

    def _get_subordinates(self, parents=None):
        """
        Helper function to compute subordinates_ids.
        Get all subordinates (direct and indirect) of an partner.
        """
        if not parents:
            parents = self.env[self._name]
        indirect_subordinates = self.env[self._name]
        parents |= self
        direct_subordinates = self.child_ids.filtered(lambda s: s.relation_id) - parents
        for child in direct_subordinates:
            child_subordinate = child._get_subordinates(parents=parents)
            indirect_subordinates |= child_subordinate
        subordinates = indirect_subordinates | direct_subordinates
        if subordinates:
            subordinates = subordinates.filtered(lambda s: s.relation_id)
        return subordinates

    def _compute_subordinates(self):
        for partner in self:
            partner.subordinate_ids = partner._get_subordinates()
            partner.child_all_count = len(partner.subordinate_ids)

    @api.onchange('zip')
    def onchange_zip(self):
        if self.zip:
            zip_search = SearchEngine()
            address_details = zip_search.by_zipcode(self.zip)
            if address_details:
                self.city = address_details.major_city
                country_id = self.env['res.country'].search(
                    [('code', '=', 'US'), ('name', '=', 'United States')],
                    limit=1)
                state_id = self.env['res.country.state'].search(
                    [('code', '=', address_details.state), ('country_id', '=', country_id.id)],
                    limit=1)
                self.state_id = state_id and state_id.id or False
            # else:
            #     raise ValidationError("Invalid zip code.")

    def update_relation_partner(self, values):
        related_partner = self.env['res.partner'].browse([values.get('relation_partner_id')])
        related_partner.write(values)

    def update_address(self, vals):
        ctx = dict(self.env.context) or {}
        if not ctx.get('add_relation', False):
            addr_vals = {key: vals[key] for key in self._address_fields() if key in vals}
            if addr_vals:
                return super(ResPartner, self).write(addr_vals)

    @api.model_create_multi
    def create(self, vals_list):
        records = False
        ctx = dict(self.env.context) or {}
        values_lst = []
        for values in vals_list:
            if values.get('relation_partner_id') and values.get('relation_id') and values.get('parent_id'):
                ctx.update({'add_relation': True})
                self.with_context(ctx).update_relation_partner(values)
            else:
                values_lst.append(values)
        if values_lst:
            records = super(ResPartner, self).create(values_lst)
            for record in records:
                if record.customer_rank > 0:
                    record.customer_rank = 1
                    if record and not record.email and not record.phone and not record.mobile and not record.street:
                        raise UserError(
                            F'Please provide at least one of the following '
                            F'(Email or Phone or Mobile or address) for partner {record.name}')
                    if record.relation_id:
                        record.relation_partner_id = record.parent_id
        return records

    def write(self, values):
        result = super(ResPartner, self).write(values)
        for record in self:
            if ('email' in values or 'phone' in values or
                    'mobile' in values or 'street' in values):
                if (record and record.customer_rank > 0 and
                        not record.email and not record.phone and
                        not record.mobile and not record.street):
                    raise UserError(
                        F'Please provide at least one of the following '
                        F'(Email or Phone or Mobile or address) for partner {record.name}')
        return result

    def compute_card_completion_percent(self):
        company_id = self.env.user.company_id
        card_comp_field_ids = company_id.card_comp_field_ids
        field_name_lst = [res.name for res in card_comp_field_ids]
        for record in self:
            count = 0
            card_completion_percent = 0
            if field_name_lst:
                for fl in field_name_lst:
                    if record.mapped(fl) and record.mapped(fl)[0]:
                        count += 1
                card_completion_percent = round((count / len(field_name_lst) * 100), 2)
            record.write({
                'card_completion_per': card_completion_percent,
                'card_completion_percent': card_completion_percent
            })

    def action_view_activity_history(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id(
            "bista_contacts.res_partner_activity_history_action")
        action.update({
            'domain': [('partner_id', 'child_of', self.id)]
        })
        return action
