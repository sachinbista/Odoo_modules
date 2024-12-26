# -*- encoding: utf-8 -*-
##############################################################################
#
#    Bista Solutions Pvt. Ltd
#    Copyright (C) 2016 (http://www.bistasolutions.com)
#
##############################################################################

from odoo import fields, models, api, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools.float_utils import float_compare
from io import BytesIO
import xlsxwriter
import base64
from collections import defaultdict
from ast import literal_eval
import math
import re
from odoo.tools import html2plaintext, is_html_empty

class Inventory(models.Model):
    _name = "stock.inventory"
    _inherit = ['stock.inventory', 'mail.thread']


    @api.model
    def default_get(self, fields):
        result = super(Inventory, self).default_get(fields)
        company_id = self.env.user.company_id
        result['adjustment_threshold'] = company_id.adjustment_threshold
        result['first_count_user_ids'] = company_id.first_count_user_ids
        result['second_count_user_ids'] = company_id.second_count_user_ids
        result['skip_threshold'] = company_id.skip_threshold
        return result

    @api.model
    def _selection_filter(self):
        """ Get the list of filter allowed according to the options checked
        in 'Settings/Warehouse'. """
        res_filter = [
            ('none', _('All products')),
            ('category', _('One product category')),
            ('product', _('One product only')),
            ('partial', _('Select products manually'))]

        if self.user_has_groups('stock.group_tracking_owner'):
            res_filter += [('owner', _('One owner only')), ('product_owner', _('One product for a specific owner'))]
        if self.user_has_groups('stock.group_production_lot'):
            res_filter.append(('lot', _('One Lot/Serial Number')))
        if self.user_has_groups('stock.group_tracking_lot'):
            res_filter.append(('pack', _('Palletize')))
        return res_filter

    currency_id = fields.Many2one(
        'res.currency', string="Currency",
        related='company_id.currency_id',
        default=lambda self: self.env.user.company_id.currency_id.id)
    adjustment_threshold = fields.Monetary(
        string="Adjustment Threshold", currency_field='currency_id',
        help="Allow threshold for adjustment, "
             "This value defines threshold for inventory adjustment", tracking=True)
    state = fields.Selection(
        selection_add=[('first_count', 'First Count'), ('second_count', 'Second Count'), ('confirm',)],
        ondelete={'approval': lambda rec: rec.write({'state': 'confirm'})}, tracking=True)
    first_count_user_ids = fields.Many2many(
        'res.users', 'first_count_users_inventory_rel', 'inventory_id', 'user_id',
        string='First Count Users')
    second_count_user_ids = fields.Many2many(
        'res.users', 'second_count_users_inventory_rel', 'inventory_id', 'user_id',
        string='Second Count Users')
    blind_count = fields.Boolean('Is Blind', copy=False, tracking=True)
    line_ids = fields.One2many(
        'stock.inventory.line', 'inventory_id', string='Inventories',
        copy=False, readonly=False,
        states={'done': [('readonly', True)]})
    first_count_user_id = fields.Many2one(
        'res.users', string='First Count User', copy=False, tracking=True)
    second_count_user_id = fields.Many2one(
        'res.users', string='Second Count User', copy=False, tracking=True)
    location_id = fields.Many2one(domain=[('usage', '=', 'internal')], tracking=True)
    access_first_count_qty = fields.Boolean(compute='compute_access_first_count_qty')
    access_second_count_qty = fields.Boolean(compute='compute_access_second_count_qty')
    show_first_count_qty = fields.Boolean(compute='compute_show_first_second_count_qty')
    show_second_count_qty = fields.Boolean(compute='compute_show_first_second_count_qty')

    # Added below fields to add tracking and track the changes.
    name = fields.Char(tracking=True)
    date = fields.Datetime(tracking=True)
    product_id = fields.Many2one(tracking=True)
    package_id = fields.Many2one(tracking=True)
    partner_id = fields.Many2one(tracking=True)
    lot_id = fields.Many2one(tracking=True)
    filter = fields.Selection(tracking=True)
    total_qty = fields.Float(tracking=True)
    category_id = fields.Many2one(tracking=True)
    exhausted = fields.Boolean(tracking=True)
    skip_threshold = fields.Boolean(string=" Skip Threshold")

    def reset_to_first_count(self):
        for record in self:
            record.update({'state': 'first_count'})

    def todo_inventory_adjustment(self):
        filename = 'ToDoInventoryAdjustments.xlsx'
        fp = BytesIO()
        workbook = xlsxwriter.Workbook(fp)
        worksheet = workbook.add_worksheet('Inventory Adjustments')
        worksheet.set_column('A:A', 32)
        worksheet.set_column('B:D', 22)
        worksheet.set_column('E:G', 30)

        heading_title = workbook.add_format({
            'bold': 1,
            'font_size': 18,
            'align': 'center',
            'font_name': 'Times New Roman',
            'text_wrap': True,
            'border': 1,
        })
        heading = workbook.add_format({
            'bold': 1,
            'font_size': 15,
            'align': 'center',
            'font_name': 'Times New Roman',
            'text_wrap': True,
        })
        content = workbook.add_format({
            'font_size': 15,
            'align': 'center',
            'font_name': 'Times New Roman',
            'text_wrap': True
        })
        content_int = workbook.add_format({
            'font_size': 15,
            'align': 'center',
            'font_name': 'Times New Roman',
            'text_wrap': True
        })

        cost_format = workbook.add_format({'num_format':'$#,##0.00','align': 'center'})
        summation_cost = workbook.add_format({'num_format':'$#,##0.00','align': 'center','bold':1})
        summation_line = workbook.add_format({'align': 'center','bold':1})


        col = 0
        row = 1

        # Create a defaultdict to store aggregated quantities for each product
        summation_qty = defaultdict(lambda: [0, 0, 0, 0])

        # Flag to determine if at least one record satisfies the condition
        any_confirmed = False
        # cost = 0
        for rec in self:
            if rec.state in ('confirm', 'first_count', 'second_count'):
                any_confirmed = True
                for line in rec.line_ids:
                    prd_name = line.product_id.name
                    cost = line.product_id.standard_price
                    theoretical_qty = line.theoretical_qty
                    real_qty = line.product_qty
                    first_count_qty = line.first_count_qty

                    # Aggregate quantities for each product
                    summation_qty[prd_name][0] += theoretical_qty
                    summation_qty[prd_name][1] += real_qty
                    summation_qty[prd_name][2] += first_count_qty
                    summation_qty[prd_name][3] += cost


        # Check if any record satisfies the condition
        if not any_confirmed:
            # worksheet.merge_range(row, 0, row, 6, 'To Process Inventory', heading_title)
            row += 2
            worksheet.write(row, col + 1, 'Product', heading)
            worksheet.write(row, col + 2, 'Cost', heading)
            worksheet.write(row, col + 3, 'System Quantity', heading)
            worksheet.write(row, col + 4, 'User Count', heading)
            worksheet.write(row, col + 5, 'Difference', heading)
            worksheet.write(row, col + 6, 'Stock Value', heading)
            # raise UserError("No confirmed records found for inventory adjustments.")

        # Write Inventory Details headers
        worksheet.merge_range(row, 0, row, 6, 'To Process Inventory', heading_title)
        row += 2
        worksheet.write(row, col , 'Product', heading)
        worksheet.write(row, col+1, 'Cost', heading)
        worksheet.write(row, col + 2, 'System Quantity', heading)
        worksheet.write(row, col + 3, 'User Count', heading)
        worksheet.write(row, col + 4, 'Difference', heading)
        worksheet.write(row, col + 5, 'Stock Value', heading)
        row += 1

        # Write aggregated quantities for each product into the worksheet
        for prd_name,  quantities in summation_qty.items():
            theoretical_qty, real_qty, first_count_qty, cost = quantities
            difference = theoretical_qty - first_count_qty if theoretical_qty > 0 else first_count_qty - theoretical_qty
            value = difference * cost

            worksheet.write(row, col, prd_name or '', content)
            worksheet.write(row, col+1, cost, cost_format)
            worksheet.write(row, col + 2, theoretical_qty, content_int)
            worksheet.write(row, col + 3, first_count_qty, content_int)
            worksheet.write(row, col + 4, difference, content_int)
            worksheet.write(row, col + 5, value, cost_format)
            row += 1

        for col in range(1, 6):
            start_cell = xlsxwriter.utility.xl_rowcol_to_cell(4, col)
            end_cell = xlsxwriter.utility.xl_rowcol_to_cell(row - 1, col)
            sum_formula = f'=SUM({start_cell}:{end_cell})'
            if col==1 or col==5:
                worksheet.write_formula(row, col, sum_formula, summation_cost)
            else:
                worksheet.write_formula(row, col, sum_formula, summation_line)

        workbook.close()
        result = base64.encodebytes(fp.getvalue())
        fp.close()

        # Create attachment
        excel_file = self.env['ir.attachment'].create({
            'name': filename,
            'datas': result,
            'res_model': 'stock.inventory',
            'type': 'binary',
        })

        # Return action to download the file
        return {
            'type': 'ir.actions.act_url',
            'url': '/web/content/%s?download=true' % (excel_file.id),
            'target': 'new',
            'nodestroy': False,
        }

    def compute_access_first_count_qty(self):
        for record in self:
            access_first_count_qty = False
            login_user = self.env.uid
            if login_user in record.first_count_user_ids.ids \
                    and record.state == 'first_count':
                access_first_count_qty = True
            record.access_first_count_qty = access_first_count_qty


    @api.model
    def open_new_batch_picking(self):
        """ Creates a new batch picking and opens client action to select its pickings.

        :return: see `action_client_action`
        """
        new_inventory_adjustment = self.env['stock.inventory'].create({})
        return new_inventory_adjustment.action_client_action_inventory()

    def action_client_action_inventory(self):
        """ Open the mobile view specialized in handling barcodes on mobile devices.

        :return: the action used to select pickings for the new batch picking
        :rtype: dict
        """
        self.ensure_one()
        action = self.env['ir.actions.actions']._for_xml_id(
            'bista_inventory_enhancement.stock_barcode_inventory_adjustment_client_action')
        action = dict(action, target='fullscreen')
        action['context'] = {'active_id': self.id}
        return action

    def action_print_inventory(self):
        return self.env.ref('sync_inventory_adjustment.action_report_inventory').report_action(self)
    
    def compute_show_first_second_count_qty(self):
        for record in self:
            show_first_count_qty = False
            show_second_count_qty = False
            login_user = self.env.uid
            first_count_user_ids = record.first_count_user_ids.ids
            second_count_user_ids = record.second_count_user_ids.ids
            if (record.state in ('confirm', 'done') or
                    (login_user in first_count_user_ids or
                     (login_user not in first_count_user_ids and
                      login_user not in second_count_user_ids))):
                show_first_count_qty = True
            if (record.state in ('confirm', 'done') or
                    (login_user in second_count_user_ids or
                     (login_user not in first_count_user_ids and
                      login_user not in second_count_user_ids))):
                show_second_count_qty = True
            record.show_first_count_qty = show_first_count_qty
            record.show_second_count_qty = show_second_count_qty

    def compute_access_second_count_qty(self):
        for record in self:
            access_second_count_qty = False
            login_user = self.env.uid
            if login_user in record.second_count_user_ids.ids \
                    and record.state == 'second_count':
                access_second_count_qty = True
            record.access_second_count_qty = access_second_count_qty

    def action_reset_product_qty(self):
        for record in self:
            if record.state == 'first_count':
                record.mapped('line_ids').write({
                    'product_qty': 0,
                    'first_count_qty': 0
                })
            elif record.state == 'second_count':
                record.mapped('line_ids').write({
                    'second_count_qty': 0
                })
        return True

    def action_start(self):
        super(Inventory, self).action_start()
        for inventory in self.filtered(lambda x: x.state not in ('done', 'cancel')):
            if inventory.filter in ('owner', 'product_owner') and not inventory.partner_id:
                raise ValidationError("Please add Inventoried Owner.")
            elif inventory.filter == 'lot' and not inventory.lot_id:
                raise ValidationError("Please add Inventoried Lot/Serial Number.")
            vals = {'state': 'first_count'}
            inventory.write(vals)
        return True

    def action_submit(self):
        for record in self:
            login_user_id = self.env.uid
            line_ids = record.line_ids
            status = record.state
            values = {}
            if status == 'first_count':
                if login_user_id in record.first_count_user_ids.ids:
                    for line in line_ids:
                        if (line.location_id.usage != 'inventory' and
                                line.product_id.tracking in ('lot', 'serial') and
                                not line.prod_lot_id):
                            raise ValidationError(
                                F"Lot/Serial number is required for the lot/serial "
                                F"tracking product {line.product_id.display_name}.")
                        if (line.location_id.usage != 'inventory' and
                                line.prod_lot_id and line.product_id.tracking == 'serial' and
                                float_compare(abs(line.first_count_qty), 1,
                                              precision_rounding=line.product_uom_id.rounding) > 0):
                            raise ValidationError(
                                _('The serial number has already been assigned: \n Product: %s, Serial Number: %s') % (
                                    line.product_id.display_name, line.prod_lot_id.name))
                        line.product_qty = line.first_count_qty
                    if  not record.skip_threshold and line_ids.filtered(
                            lambda l:
                            (abs(l.theoretical_qty - l.first_count_qty) * l.product_id.standard_price) >
                            record.adjustment_threshold):
                        status = 'second_count'
                    else:
                        status = 'confirm'
                    values.update({'first_count_user_id': self.env.uid})
                else:
                    raise ValidationError("You are not authorized to perform this operation.")
            elif status == 'second_count':
                if login_user_id in record.second_count_user_ids.ids:
                    for line in line_ids.filtered(lambda l: l.exception):
                        if (line.location_id.usage != 'inventory' and
                                line.product_id.tracking in ('lot', 'serial') and
                                not line.prod_lot_id):
                            raise ValidationError(
                                F"Lot/Serial number is required for the lot/serial "
                                F"tracking product {line.product_id.display_name}.")
                        if (line.location_id.usage != 'inventory' and
                                line.prod_lot_id and line.product_id.tracking == 'serial' and
                                float_compare(abs(line.second_count_qty), 1,
                                              precision_rounding=line.product_uom_id.rounding) > 0):
                            raise ValidationError(
                                _('The serial number has already been assigned: \n Product: %s, Serial Number: %s') % (
                                    line.product_id.display_name, line.prod_lot_id.name))
                        line.product_qty = line.second_count_qty
                    status = 'confirm'
                    values.update({'second_count_user_id': self.env.uid})
                else:
                    raise ValidationError("You are not authorized to perform this operation.")
            values.update({'state': status})
            record.write(values)

    def action_validate(self):
        for record in self:
            if not 'approval_process' in self._context:
                return record.manager_pin()
            for line in record.line_ids:
                line.product_id.inventory_adjustment_date = fields.Datetime.now()
                if (line.product_id.product_tmpl_id and
                        len(line.product_id.product_tmpl_id.product_variant_ids) == 1):
                    line.product_id.product_tmpl_id.inventory_adjustment_date = fields.Datetime.now()
        return super(Inventory, self).action_validate()

    def action_cancel_draft(self):
        for record in self:
            status = 'draft'
            if record.state != 'cancel':
                status = 'cancel'
            record.write({
                'line_ids': [(5,)],
                'state': status,
                'first_count_user_id': False,
                'second_count_user_id': False
            })

    def _get_stock_barcode_data(self):
        self = self.with_context(display_default_code=False)
        sheet_lines = self.line_ids
        lots = sheet_lines.prod_lot_id
        owners = sheet_lines.partner_id
        products = sheet_lines.product_id
        company_id = self.env.company.id

        uoms = products.uom_id | sheet_lines.product_uom_id
        # If UoM setting is active, fetch all UoM's data.
        if self.env.user.has_group('uom.group_uom'):
            uoms |= self.env['uom.uom'].search([])

        # Fetch `stock.quant.package` and `stock.package.type` if
        # group_tracking_lot.
        packages = self.env['stock.quant.package']
        package_types = self.env['stock.package.type']
        if self.env.user.has_group('stock.group_tracking_lot'):
            packages |= sheet_lines.package_id
            packages |= self.env['stock.quant.package']._get_usable_packages()
            package_types = package_types.search([])

        # Fetch `stock.location`
        source_locations = self.env['stock.location'].search([
            ('id', 'child_of', self.location_id.ids)])
        locations = sheet_lines.location_id | source_locations
        if not locations:  # `self` is an empty recordset when we open the inventory adjustment.
            if self.env.user.has_group('stock.group_stock_multi_locations'):
                locations = self.env['stock.location'].search([
                    ('usage', 'in', ['internal', 'transit']),
                    ('company_id', '=', company_id)], order='id')
            else:
                locations = self.env['stock.warehouse'].search([
                    ('company_id', '=', company_id)
                ], limit=1).lot_stock_id
        data = {
            "records": {
                "stock.inventory": self.read(
                    self._get_fields_stock_barcode(),
                    load=False),
                "stock.inventory.line": sheet_lines.read(
                    sheet_lines._get_fields_stock_barcode(),
                    load=False),
                "product.product": products.read(
                    products._get_fields_stock_barcode(),
                    load=False),
                "stock.location": locations.read(
                    locations._get_fields_stock_barcode(),
                    load=False),
                "stock.package.type": package_types.read(
                    package_types._get_fields_stock_barcode(),
                    False),
                "stock.quant.package": packages.read(
                    packages._get_fields_stock_barcode(),
                    load=False),
                "stock.lot": lots.read(
                    lots._get_fields_stock_barcode(),
                    load=False),
                "uom.uom": uoms.read(
                    uoms._get_fields_stock_barcode(),
                    load=False),
                "res.partner": owners.read(
                    owners._get_fields_stock_barcode(),
                    load=False),
            },
            "nomenclature_id": [self.env.company.nomenclature_id.id],
            "source_location_ids": source_locations.ids,
        }
        lot_data = self.env['stock.lot'].sudo().search_read(
            [('product_id', 'in', products.ids),], ['product_id', 'name']
        )
        product_ids = products.ids
        data.update({
            'lot_data': lot_data,
            'product_ids': product_ids
        })
        data['line_view_id'] = self.env.ref('bista_inventory_enhancement.inventory_line_barcode_selector').id
        return data

    def _get_fields_stock_barcode(self):
        fields = [
            'category_id',
            'filter',
            'state',
            'line_ids',
            'name',
            'location_id',
            'company_id',
            'second_count_user_ids',
            'first_count_user_ids',
        ]
        return fields.append('line_ids')

    def manager_pin(self):
        return {
                'name': 'Authentication Pin',
                'type': 'ir.actions.act_window',
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'pin.message.wizard',
                'view_id': self.env.ref('bista_inventory_enhancement.pin_message_wizard').id,
                'target': 'new',
                'context': {
                },
            }

    @api.model
    def create(self, vals):
        res = super(Inventory, self).create(vals)
        res.generate_sequence_for_inv_line_ids()
        return res

    def write(self, values):
        res = super(Inventory, self).write(values)
        for record in self:
            record.generate_sequence_for_inv_line_ids()
        return res

    
    def generate_sequence_for_inv_line_ids(self):
        res_dict = {}
        for rec in self:
            res_dict = {inv_line:inv_line.location_id.complete_name for inv_line in rec.line_ids.sorted(key=lambda s: s.id)}
            sorted_loc = []
            if res_dict:
                key_list = list(res_dict.keys()) 
                val_list = list(res_dict.values()) 

                location_name_list = res_dict.values()
                convert = lambda location_name_list: int(location_name_list) if location_name_list.isdigit() else location_name_list
                alphanum_key = lambda key: [convert(c) for c in re.split('([0-9]+)', key)]
                sorted_loc = sorted(location_name_list, key = alphanum_key)
            for count,enum_loc in enumerate(sorted_loc):
                k = key_list[val_list.index(enum_loc)]
                val_list.remove(enum_loc)
                key_list.remove(k)
                k.update({'sort_sequence': count})
        return True


class InventoryLine(models.Model):
    _inherit = "stock.inventory.line"
    _order='sort_sequence asc'

    exception = fields.Boolean(compute='get_exception', string='Exception', store=True)
    first_count_qty = fields.Float(
        'First Count Qty',
        digits='Product Unit of Measure', default=0)
    second_count_qty = fields.Float(
        'Second Count Qty',
        digits='Product Unit of Measure', default=0)
    blind_count = fields.Boolean('Is Blind', related='inventory_id.blind_count', store=True)
    state = fields.Selection("state", related='inventory_id.state')
    filter = fields.Selection(related='inventory_id.state')
    sort_sequence = fields.Integer(string='Sequence', index=True, default=0,
        help="Gives the sequence order when displaying a list of locations.")
    dummy_id = fields.Char(compute='_compute_dummy_id', inverse='_inverse_dummy_id')

    def _compute_dummy_id(self):
        self.dummy_id = ''

    def _inverse_dummy_id(self):
        pass


    def _get_fields_stock_barcode(self):
        return [
            'product_id',
            'dummy_id',
            'first_count_qty',
            'theoretical_qty',
            'product_uom_id',
            'prod_lot_id',
            'package_id',
            'location_id',
            'filter',
            'product_qty',
            'first_count_qty',
            'second_count_qty',
            'sort_sequence',
        ]

    def get_stock_barcode_data_records(self):
        products = self.product_id
        companies = self.company_id or self.env.company
        packages = self.package_id
        uoms = products.uom_id
        # If UoM setting is active, fetch all UoM's data.
        if self.env.user.has_group('uom.group_uom'):
            uoms = self.env['uom.uom'].search([])

        data = {
            "records": {
                "stock.quant": self.read(self._get_fields_stock_barcode(), load=False),
                "stock.inventory.line": self.read(self._get_fields_stock_barcode(), load=False),
                "product.product": products.read(products._get_fields_stock_barcode(), load=False),
                "stock.quant.package": packages.read(packages._get_fields_stock_barcode(), load=False),
                "res.company": companies.read(['name']),
                # "res.partner": owners.read(owners._get_fields_stock_barcode(), load=False),
                # "stock.lot": lots.read(lots._get_fields_stock_barcode(), load=False),
                "uom.uom": uoms.read(uoms._get_fields_stock_barcode(), load=False),
            },
            "nomenclature_id": [self.env.company.nomenclature_id.id],
            "user_id": self.env.user.id,
        }
        return data

    def write(self, values):
        res = super(InventoryLine, self).write(values)
        for record in self:
            record._check_no_duplicate_line()
        return res

    @api.onchange('location_id', 'product_id', 'package_id', 'product_uom_id', 'company_id', 'prod_lot_id', 'partner_id')
    def onchange_get_stock_quant(self):
        self.quant_id = False

    @api.depends('state')
    def get_exception(self):
        for record in self:
            exception = False
            if record.state not in ('draft', 'first_count', 'cancel'):
                if record.state == 'second_count':
                    diff_qty = abs(record.theoretical_qty - record.first_count_qty)
                else:
                    diff_qty = abs(record.theoretical_qty - record.second_count_qty)
                cost_diff = diff_qty * record.product_id.standard_price
                if cost_diff > 0 and cost_diff > record.inventory_id.adjustment_threshold:
                    exception = True
            record.exception = exception


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    # Override Function to add stock.quant in cache from starting point
    def _get_stock_barcode_data(self):
        # Avoid to get the products full name because code and name are separate in the barcode app.
        self = self.with_context(display_default_code=False)
        move_lines = self.move_line_ids
        lots = move_lines.lot_id
        owners = move_lines.owner_id
        # Fetch all implied products in `self` and adds last used products to avoid additional rpc.
        products = move_lines.product_id
        packagings = products.packaging_ids

        uoms = products.uom_id | move_lines.product_uom_id
        # If UoM setting is active, fetch all UoM's data.
        if self.env.user.has_group('uom.group_uom'):
            uoms |= self.env['uom.uom'].search([])

        # Fetch `stock.location`
        source_locations = self.env['stock.location'].search([('id', 'child_of', self.location_id.ids)])
        destination_locations = self.env['stock.location'].search([('id', 'child_of', self.location_dest_id.ids)])
        locations = move_lines.location_id | move_lines.location_dest_id | source_locations | destination_locations
        # Fetch `stock.quant`
        quants = self.env['stock.quant'].search([])
        # Fetch `stock.quant.package` and `stock.package.type` if group_tracking_lot.
        packages = self.env['stock.quant.package']
        package_types = self.env['stock.package.type']
        if self.env.user.has_group('stock.group_tracking_lot'):
            packages |= move_lines.package_id | move_lines.result_package_id
            packages |= self.env['stock.quant.package'].with_context(pack_locs=destination_locations.ids)._get_usable_packages()
            package_types = package_types.search([])

        data = {
            "records": {
                "stock.picking": self.read(self._get_fields_stock_barcode(), load=False),
                "stock.quant": quants.read(quants._get_fields_stock_barcode(), load=False),
                "stock.picking.type": self.picking_type_id.read(self.picking_type_id._get_fields_stock_barcode(), load=False),
                "stock.move.line": move_lines.read(move_lines._get_fields_stock_barcode(), load=False),
                # `self` can be a record set (e.g.: a picking batch), set only the first partner in the context.
                "product.product": products.with_context(partner_id=self[:1].partner_id.id).read(products._get_fields_stock_barcode(), load=False),
                "product.packaging": packagings.read(packagings._get_fields_stock_barcode(), load=False),
                "res.partner": owners.read(owners._get_fields_stock_barcode(), load=False),
                "stock.location": locations.read(locations._get_fields_stock_barcode(), load=False),
                "stock.package.type": package_types.read(package_types._get_fields_stock_barcode(), False),
                "stock.quant.package": packages.read(packages._get_fields_stock_barcode(), load=False),
                "stock.lot": lots.read(lots._get_fields_stock_barcode(), load=False),
                "uom.uom": uoms.read(uoms._get_fields_stock_barcode(), load=False),
                
            },
            "nomenclature_id": [self.env.company.nomenclature_id.id],
            "source_location_ids": source_locations.ids,
            "destination_locations_ids": destination_locations.ids,
        }
        # Extracts pickings' note if it's empty HTML.
        for picking in data['records']['stock.picking']:
            picking['note'] = False if is_html_empty(picking['note']) else html2plaintext(picking['note'])

        data['config'] = self.picking_type_id._get_barcode_config()
        data['line_view_id'] = self.env.ref('stock_barcode.stock_move_line_product_selector').id
        data['form_view_id'] = self.env.ref('stock_barcode.stock_picking_barcode').id
        data['package_view_id'] = self.env.ref('stock_barcode.stock_quant_barcode_kanban').id
        return data

