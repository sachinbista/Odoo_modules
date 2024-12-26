# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.addons import decimal_precision as dp
from odoo.exceptions import UserError, ValidationError
from odoo.tools import float_utils, float_compare
from io import BytesIO
import xlsxwriter
import base64
from datetime import datetime


class Inventory(models.Model):
    _name = "stock.inventory"
    _description = "Inventory"
    _order = "date desc, id desc"

    @api.model
    def _default_location_id(self):
        company_user = self.env.user.company_id
        warehouse = self.env['stock.warehouse'].search([('company_id', '=', company_user.id)], limit=1)
        if warehouse:
            return warehouse.lot_stock_id.id
        else:
            raise UserError(_('You must define a warehouse for the company: %s.') % (company_user.name,))

    name = fields.Char(
        'Inventory Reference',
        readonly=True, required=True,
        states={'draft': [('readonly', False)]})
    date = fields.Datetime(
        'Inventory Date',
        readonly=True, required=True,
        default=fields.Datetime.now,
        help="If the inventory adjustment is not validated, date at which the theoritical quantities have been checked.\n"
             "If the inventory adjustment is validated, date at which the inventory adjustment has been validated.")
    line_ids = fields.One2many(
        'stock.inventory.line', 'inventory_id', string='Inventories',
        copy=True, readonly=False,
        states={'done': [('readonly', True)]})
    move_ids = fields.One2many(
        'stock.move', 'inventory_id', string='Created Moves',
        states={'done': [('readonly', True)]})
    state = fields.Selection(string='Status', selection=[
        ('draft', 'Draft'),
        ('cancel', 'Cancelled'),
        ('confirm', 'In Progress'),
        ('done', 'Validated')],
        copy=False, index=True, readonly=True,
        default='draft')
    company_id = fields.Many2one(
        'res.company', 'Company',
        readonly=True, index=True, required=True,
        states={'draft': [('readonly', False)]},
        default=lambda self: self.env['res.company']._company_default_get('stock.inventory'))
    location_id = fields.Many2one(
        'stock.location', 'Inventoried Location',
        readonly=True, required=True,
        states={'draft': [('readonly', False)]},
        default=_default_location_id)
    product_id = fields.Many2one(
        'product.product', 'Inventoried Product',
        readonly=True,
        states={'draft': [('readonly', False)]},
        help="Specify Product to focus your inventory on a particular Product.")
    package_id = fields.Many2one(
        'stock.quant.package', 'Inventoried Pack',
        readonly=True,
        states={'draft': [('readonly', False)]},
        help="Specify Pack to focus your inventory on a particular Pack.")
    partner_id = fields.Many2one(
        'res.partner', 'Inventoried Owner',
        readonly=True,
        states={'draft': [('readonly', False)]},
        help="Specify Owner to focus your inventory on a particular Owner.")
    lot_id = fields.Many2one(
        'stock.lot', 'Inventoried Lot/Serial Number',
        copy=False, readonly=True,
        states={'draft': [('readonly', False)]},
        help="Specify Lot/Serial Number to focus your inventory on a particular Lot/Serial Number.")
    filter = fields.Selection(
        string='Inventory of', selection='_selection_filter',
        required=True,
        default='none',
        help="If you do an entire inventory, you can choose 'All Products' and it will prefill the inventory with the current stock.  If you only do some products  "
             "(e.g. Cycle Counting) you can choose 'Manual Selection of Products' and the system won't propose anything.  You can also let the "
             "system propose for a single product / lot /... ")
    total_qty = fields.Float('Total Quantity', compute='_compute_total_qty')
    category_id = fields.Many2one(
        'product.category', 'Product Category',
        readonly=True, states={'draft': [('readonly', False)]},
        help="Specify Product Category to focus your inventory on a particular Category.")
    exhausted = fields.Boolean('Include Exhausted Products', readonly=True, states={'draft': [('readonly', False)]})

    @api.depends('product_id', 'line_ids.product_qty')
    def _compute_total_qty(self):
        """ For single product inventory, total quantity of the counted """
        self.ensure_one()
        if self.product_id:
            self.total_qty = sum(self.mapped('line_ids').mapped('product_qty'))
        else:
            self.total_qty = 0

    def _exhausted_products(self):
        exhausted = ''
        if self.exhausted:
            exhausted = 'Yes'
        else:
            exhausted = 'No'
        return exhausted

    def export_stock_inventory(self):
        filename = 'InventoryAdjustments.xlsx'
        fp = BytesIO()
        workbook = xlsxwriter.Workbook(fp)
        worksheet = workbook.add_worksheet('Inventory Adjustments')
        worksheet.set_column('A:A', 32)
        worksheet.set_column('B:D', 22)
        worksheet.set_column('E:G', 30)

        heading_title = workbook.add_format({
            'bold':1,
            'font_size' : 18,
            'align' : 'center',
            'font_name' : 'Times New Roman',
            'text_wrap': True,
            'border':1,
        })
        heading = workbook.add_format({
            'bold':1,
            'font_size' : 15,
            'align' : 'left',
            'font_name' : 'Times New Roman',
            'text_wrap': True,
        })
        content = workbook.add_format({
            'font_size' : 15,
            'align' : 'left',
            'font_name' : 'Times New Roman',
            'text_wrap': True
        })
        content_int = workbook.add_format({
            'font_size' : 15,
            'align' : 'right',
            'font_name' : 'Times New Roman',
            'text_wrap': True
        })

        col = 0
        row = 1
        for rec in self:
            worksheet.merge_range(row, 0, row+1, 6, 'Inventory Adjustments', heading_title)

            inventory_name = ''
            filter_prd = ''
            filter_val = ''
            exhausted_label = ''
            exhausted = ''

            if rec.filter == 'none':
                inventory_name = 'All Products'
                exhausted_label = 'Include Exhausted Products'
                exhausted = rec._exhausted_products()
            if rec.filter == 'category':
                inventory_name = 'One product category'
                filter_prd = 'Product Category'
                filter_val = rec.category_id.name
                exhausted_label = 'Include Exhausted Products'
                exhausted = rec._exhausted_products()
            if rec.filter == 'product':
                inventory_name = 'One product only'
                filter_prd = 'Inventoried Product'
                filter_val = rec.product_id.name
            if rec.filter == 'partial':
                inventory_name = 'Select products manually'
            if rec.filter == 'lot':
                inventory_name = 'One Lot/Serial Number'
                filter_prd = 'Inventoried Lot/Serial Number'
                filter_val = rec.lot_id.name

            state = ''
            if rec.state == 'draft':
                state = 'Draft'
            if rec.state == 'cancel':
                state = 'Cancelled'
            if rec.state == 'confirm':
                state = 'In Progress'
            if rec.state == 'done':
                state = 'Validated'

            date_inv = datetime.strftime(rec.date, '%m/%d/%Y %H:%M:%S') if rec.date else ''

            row += 4
            worksheet.write(row, col, "Inventory Reference", heading)
            worksheet.write(row+1, col,"Inventoried Location", heading)
            worksheet.write(row+2, col,"Inventory of", heading)
            worksheet.write(row+3, col,"Status", heading)
            worksheet.write(row, col+4, "Inventory Date", heading)
            worksheet.write(row+1, col+4,"Company", heading)
            if filter_prd:
                worksheet.write(row+2, col+4, filter_prd, heading)
                worksheet.write(row+3, col+4, exhausted_label, heading)
            else:
                worksheet.write(row+2, col+4, exhausted_label, heading)

            worksheet.write(row, col+1, rec.name, content)
            worksheet.write(row+1, col+1, rec.location_id and rec.location_id.display_name or '', content)
            worksheet.write(row+2, col+1, inventory_name, content)
            worksheet.write(row+3, col+1, state, content)
            worksheet.write(row, col+5, date_inv, content)
            worksheet.write(row+1, col+5, rec.company_id.name, content)
            if filter_val:
                worksheet.write(row+2, col+5, filter_val or '', content)
                worksheet.write(row+3, col+5, exhausted, content)
            else:
                worksheet.write(row+2, col+5, exhausted, content)

            if rec.line_ids:
                row += 5
                worksheet.merge_range(row, 0, row, 6, 'Inventory Details', heading_title)
                row += 2
                worksheet.write(row, col, 'Product', heading)
                worksheet.write(row, col+1, 'UOM', heading)
                worksheet.write(row, col+2, 'Location', heading)
                worksheet.write(row, col+3, 'Lot/Serial Number', heading)
                worksheet.write(row, col+4, 'Pack', heading)
                worksheet.write(row, col+5, 'Theoritical Quantity', heading)
                worksheet.write(row, col+6, 'Real Quantity', heading)

                row += 1
                for line in rec.line_ids:
                    prd_name = ''
                    if line.product_id.default_code and line.product_id.name:
                        prd_name = '[' + line.product_id.default_code + '] ' + line.product_id.name
                    else:
                        prd_name = line.product_id.name
                    worksheet.write(row, col, prd_name or '', content)
                    worksheet.write(row, col+1, line.product_uom_id and line.product_uom_id.name or '', content)
                    worksheet.write(row, col+2, line.location_id and line.location_id.display_name or '', content)
                    worksheet.write(row, col+3, line.prod_lot_id and line.prod_lot_id.name or '', content)
                    worksheet.write(row, col+4, line.package_id and line.package_id.name or '', content)
                    worksheet.write(row, col+5, "{:.2f}".format(line.theoretical_qty), content_int)
                    worksheet.write(row, col+6, "{:.2f}".format(line.product_qty), content_int)
                    row += 1
                row += 1

        workbook.close()
        result = base64.encodebytes(fp.getvalue())

        fp.close()
        excel_file = self.env['ir.attachment'].create({
            'name': filename,
            'datas': result,
            'res_model': 'stock.inventory',
            # 'res_id': self.id,
            'type': 'binary',
        })
        return {
            'type': 'ir.actions.act_url',
            'url': '/web/content/%s?download=true' %  (excel_file.id),
            'target': 'new',
            'nodestroy': False,
        }

    @api.onchange('filter')
    def _onchange_filter(self):
        if self.filter not in ('product', 'product_owner'):
            self.product_id = False
        if self.filter != 'lot':
            self.lot_id = False
        if self.filter not in ('owner', 'product_owner'):
            self.partner_id = False
        if self.filter != 'pack':
            self.package_id = False
        if self.filter != 'category':
            self.category_id = False
        if self.filter != 'product':
            self.exhausted = False
        if self.filter == 'product':
            self.exhausted = True

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
            res_filter.append(('pack', _('A Pack')))
        return res_filter

    def action_reset_product_qty(self):
        self.mapped('line_ids').write({'product_qty': 0})
        return True

    def action_validate(self):
        lines = self.line_ids.filtered(lambda l: l.theoretical_qty != l.product_qty)
        for line in lines:
            if not line.quant_id:
                quants = self.env['stock.quant']._gather(line.product_id, line.location_id, lot_id=line.prod_lot_id, package_id=line.package_id, owner_id=None, strict=True)
                line.quant_id = quants and quants.id
                if not quants:
                    line.quant_id = self.env['stock.quant'].create({
                        'product_id': line.product_id.id,
                        'location_id': line.location_id.id,
                        'inventory_quantity': line.product_qty,
                        'lot_id': line.prod_lot_id and line.prod_lot_id.id,
                    })
            line.quant_id.inventory_quantity = line.product_qty
            # line.quant_id.with_context(inventory_id=self.id).action_apply_inventory()
            line.quant_id.with_context(inventory_id=self.id)._apply_inventory()
            line.quant_id.inventory_quantity_set = False
        self.write({'state': 'done', 'date': fields.Datetime.now()})

    def action_cancel_draft(self):
        self.write({
            'line_ids': [(5,)],
            'state': 'draft'
        })

    def action_start(self):
        for inventory in self.filtered(lambda x: x.state not in ('done','cancel')):
            vals = {'state': 'confirm', 'date': fields.Datetime.now()}
            if (inventory.filter != 'partial') and not inventory.line_ids:
                vals.update({'line_ids': [(0, 0, line_values) for line_values in inventory._get_inventory_lines_values()]})
            inventory.write(vals)
        return True

    def _get_inventory_lines_values(self):
        # TDE CLEANME: is sql really necessary ? I don't think so
        locations = self.env['stock.location'].search([('id', 'child_of', [self.location_id.id])])
        domain = ' location_id in %s AND quantity != 0 AND active = TRUE'
        args = (tuple(locations.ids),)

        vals = []
        Product = self.env['product.product']
        # Empty recordset of products available in stock_quants
        quant_products = self.env['product.product']
        # Empty recordset of products to filter
        products_to_filter = self.env['product.product']

        # case 0: Filter on company
        if self.company_id:
            domain += ' AND company_id = %s'
            args += (self.company_id.id,)

        #case 1: Filter on One owner only or One product for a specific owner
        if self.partner_id:
            domain += ' AND owner_id = %s'
            args += (self.partner_id.id,)
        #case 2: Filter on One Lot/Serial Number
        if self.lot_id:
            domain += ' AND lot_id = %s'
            args += (self.lot_id.id,)
        #case 3: Filter on One product
        if self.product_id:
            domain += ' AND product_id = %s'
            args += (self.product_id.id,)
            products_to_filter |= self.product_id
        #case 4: Filter on A Pack
        if self.package_id:
            domain += ' AND package_id = %s'
            args += (self.package_id.id,)
        #case 5: Filter on One product category + Exahausted Products
        if self.category_id:
            categ_products = Product.search([('categ_id', 'child_of', self.category_id.id)])
            domain += ' AND product_id = ANY (%s)'
            args += (categ_products.ids,)
            products_to_filter |= categ_products

        self.env.cr.execute("""SELECT stock_quant.id as quant_id, product_id, sum(quantity) as product_qty, location_id, lot_id as prod_lot_id, package_id, owner_id as partner_id
            FROM stock_quant
            LEFT JOIN product_product
            ON product_product.id = stock_quant.product_id
            WHERE %s
            GROUP BY stock_quant.id, product_id, location_id, lot_id, package_id, partner_id """ % domain, args)

        for product_data in self.env.cr.dictfetchall():
            # replace the None the dictionary by False, because falsy values are tested later on
            for void_field in [item[0] for item in product_data.items() if item[1] is None]:
                product_data[void_field] = False
            product_data['theoretical_qty'] = product_data['product_qty']
            product_data['quant_id'] = product_data['quant_id']
            if product_data['product_id']:
                product_data['product_uom_id'] = Product.browse(product_data['product_id']).uom_id.id
                quant_products |= Product.browse(product_data['product_id'])
            vals.append(product_data)
        if self.exhausted:
            exhausted_vals = self._get_exhausted_inventory_line(products_to_filter, quant_products)
            vals.extend(exhausted_vals)
        return vals

    def _get_exhausted_inventory_line(self, products, quant_products):
        '''
        This function return inventory lines for exausted products
        :param products: products With Selected Filter.
        :param quant_products: products available in stock_quants
        '''
        vals = []
        exhausted_domain = [('type', 'not in', ('service', 'consu', 'digital'))]
        if products:
            exhausted_products = products - quant_products
            exhausted_domain += [('id', 'in', exhausted_products.ids)]
        else:
            exhausted_domain += [('id', 'not in', quant_products.ids)]
        exhausted_products = self.env['product.product'].search(exhausted_domain)
        for product in exhausted_products:
            vals.append({
                'inventory_id': self.id,
                'product_id': product.id,
                'location_id': self.location_id.id,
                'product_uom_id': product.uom_id.id,
            })
        return vals


class InventoryLine(models.Model):
    _name = "stock.inventory.line"
    _description = "Inventory Line"
    _order = "product_id, inventory_id, location_id, prod_lot_id"

    inventory_id = fields.Many2one(
        'stock.inventory', 'Inventory',
        index=True, ondelete='cascade')
    partner_id = fields.Many2one('res.partner', 'Owner')
    product_id = fields.Many2one(
        'product.product', 'Product',
        domain=[('type', '=', 'product')],
        index=True, required=True)
    product_uom_id = fields.Many2one(
        'uom.uom', 'Product Unit of Measure',
        required=True)
    product_uom_category_id = fields.Many2one(string='Uom category', related='product_uom_id.category_id', readonly=True)
    product_qty = fields.Float(
        'Checked Quantity',
        digits='Product Unit of Measure', default=0)
    location_id = fields.Many2one(
        'stock.location', 'Location',
        index=True, required=True)
    package_id = fields.Many2one(
        'stock.quant.package', 'Pack', index=True)
    prod_lot_id = fields.Many2one(
        'stock.lot', 'Lot/Serial Number',
        domain="[('product_id','=',product_id)]")
    company_id = fields.Many2one(
        'res.company', 'Company', related='inventory_id.company_id',
        index=True, readonly=True, store=True)
    # TDE FIXME: necessary ? -> replace by location_id
    state = fields.Selection(
        string='Status',  related='inventory_id.state', readonly=True)
    theoretical_qty = fields.Float(
        'Theoretical Quantity', compute='_compute_theoretical_qty',
        digits='Product Unit of Measure', readonly=True, store=True)
    inventory_location_id = fields.Many2one(
        'stock.location', 'Inventory Location', related='inventory_id.location_id', related_sudo=False, readonly=False)
    product_tracking = fields.Selection(string='Tracking', related='product_id.tracking', readonly=True)

    quant_id = fields.Many2one('stock.quant', string='Quants')

    @api.depends('location_id', 'product_id', 'package_id', 'product_uom_id', 'company_id', 'prod_lot_id', 'partner_id')
    def _compute_theoretical_qty(self,product_id=None,lot_id=None,owner_id=None,to_uom=None):
        for rec in self:
            if not rec.product_id:
                rec.theoretical_qty = 0
                return
            theoretical_qty = rec.product_id.get_theoretical_quantity(
                rec.product_id.id,
                rec.location_id.id,
                lot_id=rec.prod_lot_id.id,
                package_id=rec.package_id.id,
                owner_id=rec.partner_id.id,
                to_uom=rec.product_uom_id.id,
            )
            rec.theoretical_qty = theoretical_qty

    @api.onchange('product_id')
    def _onchange_product(self):
        # If no UoM or incorrect UoM put default one from product
        if self.product_id:
            self.product_uom_id = self.product_id.uom_id.id

    @api.model_create_multi
    def create(self, vals_list):
        """ Override to handle the case we create inventory line without
        `theoretical_qty` because this field is usually computed, but in some
        case (typicaly in tests), we create inventory line without trigger the
        onchange, so in this case, we set `theoretical_qty` depending of the
        product's theoretical quantity.
        Handles the same problem with `product_uom_id` as this field is normally
        set in an onchange of `product_id`.
        Finally, this override checks we don't try to create a duplicated line.
        """
        products = self.env['product.product'].browse([vals.get('product_id') for vals in vals_list])
        for product, values in zip(products, vals_list):
            if 'theoretical_qty' not in values:
                theoretical_qty = self.env['product.product'].get_theoretical_quantity(
                    values['product_id'],
                    values['location_id'],
                    lot_id=values.get('prod_lot_id'),
                    package_id=values.get('package_id'),
                    owner_id=values.get('partner_id'),
                    to_uom=values.get('product_uom_id'),
                )
                values['theoretical_qty'] = theoretical_qty
            if 'product_id' in values and 'product_uom_id' not in values:
                values['product_uom_id'] = product.product_tmpl_id.uom_id.id
        res = super(InventoryLine, self).create(vals_list)
        res._check_no_duplicate_line()
        return res

    def _check_no_duplicate_line(self):
        domain = [
            ('product_id', 'in', self.product_id.ids),
            ('location_id', 'in', self.location_id.ids),
            '|', ('partner_id', 'in', self.partner_id.ids), ('partner_id', '=', None),
            '|', ('package_id', 'in', self.package_id.ids), ('package_id', '=', None),
            '|', ('prod_lot_id', 'in', self.prod_lot_id.ids), ('prod_lot_id', '=', None),
            '|', ('inventory_id', 'in', self.inventory_id.ids), ('inventory_id', '=', None),
        ]
        groupby_fields = ['product_id', 'location_id', 'partner_id', 'package_id', 'prod_lot_id', 'inventory_id']
        lines_count = {}
        for group in self.read_group(domain, ['product_id'], groupby_fields, lazy=False):
            key = tuple([group[field] and group[field][0] for field in groupby_fields])
            lines_count[key] = group['__count']
        for line in self:
            key = (line.product_id.id, line.location_id.id, line.partner_id.id, line.package_id.id, line.prod_lot_id.id, line.inventory_id.id)
            if lines_count[key] > 1:
                raise UserError(_("There is already one inventory adjustment line for this product,"
                                  " you should rather modify this one instead of creating a new one."))