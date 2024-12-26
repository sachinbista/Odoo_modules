from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from itertools import groupby
from datetime import datetime
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
import calendar
from datetime import timedelta, date



class TransferPackage(models.TransientModel):
    _name = 'transfer.package'
    _description = 'Internal Transfer from Stock Quant.'

    dest_location_id = fields.Many2one('stock.location', string="Destination Location")
    # line_ids = fields.One2many('transfer.package.line', 'transfer_package_id', string="Transfer Package Lines")
    quant_ids = fields.Many2one('stock.quant')

    # @api.model
    # def _fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
    #     res = super(CreateTransfer, self)._fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar,
    #                                                     submenu=submenu)
    #     context = self._context
    #     if not context:
    #         context = {}
    #     active_ids = context.get('active_ids', [])
    #     active_model = context.get('active_model', '')
    #     if active_ids and active_model == 'product.warehouse.inventory':
    #         record_with_is_core = self.env['product.warehouse.inventory'].search([('id', 'in', active_ids), ('is_core','=', True)])
    #         if record_with_is_core:
    #             product_names = record_with_is_core.mapped('product_id.default_code')
    #             product_names =','.join(product_names)
    #             raise UserError("Invalid Operation for these Core Products  %s.\nYou can perform this operation from Core Inventory Report." % (product_names))
    #     elif active_ids and active_model == 'stock.quant':
    #         record_with_is_core = self.env['stock.quant'].search([('id', 'in', active_ids), ('product_id.is_core','=', True), ('move_options','=', 'new_product')])
    #         if record_with_is_core:
    #             product_names = record_with_is_core.mapped('product_id.default_code')
    #             product_names =','.join(product_names)
    #             raise UserError("Invalid Operation Action(New) for these Core Products  %s.\nYou cannot perform this operation." % (product_names))
    #     return res


    # @api.model
    # def default_get(self, fields):
    #     res = super(TransferPackage, self).default_get(fields)
    #     is_core = self.env.context.get('is_core')
    #     stock_warehouse_obj = self.env['stock.warehouse']
    #     if is_core:
    #         raise UserError("Invalid Operation ! You can perform this operation from Core Inventory Report.")
    #     if not self.env.context.get('type') == 'core_internal_transfer' and not self.env.context.get(
    #             'type') == 'internal_company_transfer':
    #         branch_id = False
    #         if self.env.user.branch_id:
    #             branch_id = self.env.user.branch_id.id
    #         warehouse_id = stock_warehouse_obj.search([('branch_id', '=', branch_id)], limit=1)
    #         des_warehouse_id = stock_warehouse_obj.search([('branch_id', '=', self.env.user.branch_id.id)], limit=1)
    #         active_ids = self._context.get('active_ids')
    #         if not active_ids:
    #             raise UserError("Please select any record!")
    #
    #         active_ids = self.env['product.warehouse.inventory'].browse(active_ids)
    #         lines = []
    #         for rec in active_ids:
    #             # if rec.qty_available > 0:
    #             rec_warehouse_id = rec.warehouse_id.id
    #             lines.append((0, 0, {'warehouse_id': rec_warehouse_id,
    #                                  'product_id': rec.product_id.id,
    #                                  'qty_available': rec.qty_available,
    #                                  'qty_transfer': 0,
    #                                  # 'des_warehouse_id':warehouse_id.id,
    #                                  'company_id': rec.company_id.id,
    #                                  'des_warehouse_id': des_warehouse_id.id if rec_warehouse_id != des_warehouse_id.id else False
    #                                  }))
    #
    #         res.update({
    #             'branch_id': branch_id,
    #             'line_ids': lines,
    #             'wh_product_ids': active_ids.ids,
    #             'warehouse_id': warehouse_id.id,
    #         })
    #     elif self.env.context.get('type') == 'internal_company_transfer':
    #         warehouse_rec = self.env['stock.warehouse']
    #         branch_id = False
    #         if self.env.user.branch_id:
    #             branch_id = self.env.user.branch_id.id
    #         active_ids = self._context.get('active_ids')
    #         if not active_ids:
    #             raise UserError("Please select any record!")
    #         active_ids = self.env['stock.quant'].browse(active_ids)
    #         des_warehouse_id = stock_warehouse_obj.search([('branch_id', '=', self.env.user.branch_id.id)], limit=1)
    #         lines = []
    #         for rec in active_ids:
    #             move_option = rec.move_options
    #             src_warehouse_id = rec.location_id.sudo().get_warehouse()
    #             lines.append((0, 0, {
    #                 'product_id': rec.product_id.id,
    #                 'qty_available': rec.quantity,
    #                 'qty_transfer': 0,
    #                 'company_id': rec.company_id.id,
    #                 'source_location_id': rec.location_id.id,
    #                 'brnch_id': src_warehouse_id.branch_id.id,
    #                 'quant_action': move_option,
    #                 # 'destination_location_id':des_warehouse_id.lot_stock_id.id
    #             }))
    #
    #         res.update({
    #             'branch_id': branch_id,
    #             'line_ids': lines,
    #         })
    #
    #
    #     elif self.env.context.get('type') == 'core_internal_transfer':
    #         warehouse_rec = self.env['stock.warehouse']
    #         branch_id = False
    #         if self.env.user.branch_id:
    #             branch_id = self.env.user.branch_id.id
    #         active_ids = self._context.get('active_ids')
    #         if not active_ids:
    #             raise UserError("Please select any record!")
    #         active_ids = self.env['stock.quant'].browse(active_ids)
    #         lines = []
    #         for rec in active_ids:
    #             src_warehouse_id = rec.location_id.get_warehouse()
    #             if rec.move_options == 'new_product':
    #                 move_option = False
    #             else:
    #                 move_option = rec.move_options
    #             if rec.product_id.is_core:
    #                 lines.append((0, 0, {
    #                     'product_id': rec.product_id.id,
    #                     'qty_available': rec.quantity,
    #                     'qty_transfer': rec.quantity,
    #                     'company_id': rec.company_id.id,
    #                     'quant_action': move_option,
    #                     'warehouse_id': src_warehouse_id.id,
    #                     'core_location_id': rec.location_id.id,
    #                     'is_core_product': True
    #                 }))
    #             else:
    #                 lines.append((0, 0, {
    #                     'product_id': rec.product_id.id,
    #                     'qty_available': rec.quantity,
    #                     'qty_transfer': rec.quantity,
    #                     'company_id': rec.company_id.id,
    #                     'quant_action': move_option,
    #                     'warehouse_id': src_warehouse_id.id,
    #                     'core_location_id': rec.location_id.id,
    #                 }))
    #
    #         res.update({
    #             'branch_id': branch_id,
    #             'line_ids': lines,
    #         })
    #     return res


    # def action_next_step(self):
    #     picking_vals_list = {}
    #     if not self.line_ids:
    #         raise UserError("Please select some lines for transfer!")
    #     lines_qty_transfer = self.line_ids.filtered(
    #             lambda line: line.qty_transfer > 0)
    #     if not lines_qty_transfer:
    #         raise UserError("Qty To Transfer should be greater than 0.")
    #
    #     if not self.env.context.get('type') == 'internal_company_transfer':
    #         lines_to_process = self.line_ids.filtered(
    #                 lambda line: line.warehouse_id.id != line.des_warehouse_id.id and line.qty_transfer > 0)
    #         if not lines_to_process:
    #             raise UserError("Please correct Destination Warehouse. Destination Warehouse should be different than Source Warehouse.")
    #         for line in self.line_ids:
    #             if line.warehouse_id.id == line.des_warehouse_id.id:
    #                 raise UserError("Please correct Destination Warehouse. Destination Warehouse should be different than Source Warehouse.")
    #     else:
    #         lines_to_process = self.line_ids.filtered(
    #             lambda line: line.source_location_id.id != line.destination_location_id.id and line.qty_transfer > 0)
    #         if not lines_to_process:
    #             raise UserError(
    #                 "Please correct Destination location. Destination location should be different than Source location.")
    #         for line in self.line_ids:
    #             if line.source_location_id.id == line.destination_location_id.id:
    #                 raise UserError(
    #                     "Please correct location Warehouse. Destination location should be different than Source location.")
    #
    #     # for line in lines_to_process:
    #     #     if picking_vals_list.get(line.warehouse_id):
    #     #         picking_vals_list[line.warehouse_id].append(line)
    #     #     else:
    #     #         picking_vals_list.update({line.warehouse_id : [line]})
    #     for line in lines_to_process:
    #         if self.env.context.get('type') == 'internal_company_transfer':
    #             src_warehouse_id = line.source_location_id.get_warehouse()
    #             des_warehouse_id=line.destination_location_id.get_warehouse()
    #             key = str(src_warehouse_id.id) + '-' + str(des_warehouse_id.id)
    #         else:
    #             key = str(line.warehouse_id.id) + '-' + str(line.des_warehouse_id.id)
    #         if picking_vals_list.get(key):
    #             picking_vals_list[key].append(line)
    #         else:
    #             picking_vals_list.update({key: [line]})
    #     if not self.env.context.get('type') == 'internal_company_transfer':
    #         picking_id_list = self.create_pickings(picking_vals_list)
    #     else:
    #         picking_id_list = self.create_internal_picking(picking_vals_list)
    #     transfer_picking_ids = picking_id_list
    #     action = self.env.ref('stock.action_picking_tree_all').sudo().read()[0]
    #     if action.get('context'):
    #         action_context = "{'contact_display': 'partner_address', 'default_company_id': allowed_company_ids[0]}"
    #         action.update({'context': action_context})
    #     if len(transfer_picking_ids) > 1:
    #         action['domain'] = [('id', 'in', transfer_picking_ids)]
    #     elif len(transfer_picking_ids) == 1:
    #         form_view = [(self.env.ref('stock.view_picking_form').id, 'form')]
    #         if 'views' in action:
    #             action['views'] = form_view + [(state, view) for state, view in action['views'] if view != 'form']
    #         else:
    #             action['views'] = form_view
    #         action['res_id'] = transfer_picking_ids[0]
    #     else:
    #         action = {'type': 'ir.actions.act_window_close'}
    #     return action
    #
    # def create_internal_picking(self, picking_vals_list):
    #
    #     picking_obj = self.env['stock.picking']
    #     move_obj = self.env['stock.move']
    #     pwi_obj = self.env['product.warehouse.inventory']
    #     picking_list = []
    #
    #     for warehouse_id, product_line in picking_vals_list.items():
    #
    #         des_warehouse_id = []
    #         warehouse_id = self.env['stock.warehouse'].browse(int(warehouse_id.split("-")[0]))
    #         # code for create out picking
    #         group_id = self.env['procurement.group'].create({
    #             'name': warehouse_id.name, 'move_type': 'one',
    #         })
    #         for line in product_line:
    #             if not des_warehouse_id:
    #                 des_warehouse_id.append(line.destination_location_id)
    #                 if not des_warehouse_id[0]:
    #                     raise ValidationError("Please Select Destination !")
    #
    #         vals = {
    #             'picking_type_id': warehouse_id.int_type_id.id,
    #             'date': fields.Datetime.now(),
    #             'origin': 'Internal Transfer To' + des_warehouse_id[0].name,
    #             'location_dest_id': des_warehouse_id[0].id,
    #             'location_id': warehouse_id.lot_stock_id.id,
    #             'company_id': self.env.user.company_id.id,
    #             'group_id': group_id.id,
    #             'branch_id': warehouse_id.branch_id.id,
    #             'note': self.note
    #         }
    #         picking_id_1 = picking_obj.sudo().create(vals)
    #         picking_list.append(picking_id_1.id)
    #         move_list = []
    #         for line in product_line:
    #             if warehouse_id.id == des_warehouse_id[0].id:
    #                 raise UserError("Source and destination warehouse should not be different for product %s" % (
    #                     line.product_id.name_get()[0][1]))
    #             move_vals = {
    #                 'name': (picking_id_1.name or '')[:2000],
    #                 'product_id': line.product_id.id,
    #                 'product_uom': line.product_id.uom_id.id,
    #                 'product_uom_qty': line.qty_transfer,
    #                 # 'date': sched_date_val,
    #                 'location_id': line.source_location_id.id,
    #                 'location_dest_id': des_warehouse_id[0].id,
    #                 'picking_id': picking_id_1.id,
    #                 'company_id': self.env.user.company_id.id,
    #                 'picking_type_id': warehouse_id.int_type_id.id,
    #                 'group_id': group_id.id,
    #                 'origin': picking_id_1.name,
    #                 'warehouse_id': warehouse_id.id,
    #                 'branch_id': line.brnch_id.id,
    #                 'move_options': line.quant_action if line.quant_action else False,
    #                 'note': line.notes,
    #
    #             }
    #             move_list.append(move_vals)
    #             move_1 = move_obj.sudo().create(move_list)
    #             picking_id_1.sudo().action_confirm()
    #             picking_id_1.sudo().action_assign()
    #
    #     return picking_list
    #
    # def create_pickings(self, picking_vals_list):
    #
    #     picking_obj = self.env['stock.picking']
    #     move_obj = self.env['stock.move']
    #     pwi_obj = self.env['product.warehouse.inventory']
    #     picking_list = []
    #     src_list = []
    #
    #     for warehouse_id, product_line in picking_vals_list.items():
    #         sche_date_list = []
    #         sche_receive_list = []
    #         sched_date_val = False
    #         receive_sched_date_val = False
    #
    #         des_warehouse_id = []
    #         warehouse_id = self.env['stock.warehouse'].browse(int(warehouse_id.split("-")[0]))
    #         # code for create out picking
    #         group_id = self.env['procurement.group'].create({
    #             'name': warehouse_id.name, 'move_type': 'one',
    #         })
    #         transit_location_id = self.env['stock.location'].search([
    #             ('usage', '=', 'transit'),
    #             ('active', '=', True),
    #         ], limit=1)
    #         for line in product_line:
    #             if not des_warehouse_id:
    #                 des_warehouse_id.append(line.des_warehouse_id)
    #                 if not des_warehouse_id[0]:
    #                     raise ValidationError("Please Select Destination !")
    #         # truck_sched_id=self.env['trucks.schedule'].search([('location_id','=',line.warehouse_id.lot_stock_id.id),('sends_to_loc_ids','in',(line.des_warehouse_id.lot_stock_id.id))],limit=1)
    #         # if truck_sched_id :
    #         #     todayDate = datetime.today()
    #         #     dateDay = {dt.strftime("%A"): dt for x in range(7) for dt in [todayDate + timedelta(x)]}
    #         #     sched_date_val=dateDay[truck_sched_id.delivery_days]
    #         # else:
    #         #     sched_date_val = fields.Datetime.now()
    #
    #         truck_sched_id = self.env['trucks.schedule'].sudo().search(
    #             [('location_id', '=', self.warehouse_id.lot_stock_id.id), (
    #                 'sends_to_loc_ids', 'in', (line.des_warehouse_id.lot_stock_id.id))])
    #         for line in truck_sched_id:
    #             if line:
    #                 todayDate = datetime.today()
    #                 dateDay = {dt.strftime("%A"): dt for x in range(7) for dt in [todayDate + timedelta(x)]}
    #                 sched_date_val = dateDay[line.delivery_days]
    #                 sche_date_list.append(sched_date_val)
    #         if sched_date_val:
    #             scheduledatelist = min(sche_date_list)
    #             if scheduledatelist:
    #                 sched_date_val = scheduledatelist
    #         else:
    #             sched_date_val = fields.Datetime.now()
    #         if product_line[0].is_core_product:
    #             vals = {
    #                 'picking_type_id': warehouse_id.int_type_id.id,
    #                 # 'date': fields.Datetime.now(),
    #                 'date': sched_date_val,
    #                 'origin': 'Warehouse Inventory Transfer to ' + des_warehouse_id[0].name,
    #                 'location_dest_id': transit_location_id.id,
    #                 'location_id': product_line[0].core_location_id.id,
    #                 'company_id': self.env.user.company_id.id,
    #                 'group_id': group_id.id,
    #                 'branch_id': warehouse_id.branch_id.id,
    #                 'is_intra_com': True,
    #                 'src_warehouse_id': warehouse_id.id,
    #                 'dest_warehouse_id': des_warehouse_id[0].id
    #             }
    #         else:
    #             vals = {
    #                 'picking_type_id': warehouse_id.int_type_id.id,
    #                 'date': sched_date_val,
    #                 'origin': 'Warehouse Inventory Transfer to ' + des_warehouse_id[0].name,
    #                 'location_dest_id': transit_location_id.id,
    #                 'location_id': warehouse_id.lot_stock_id.id,
    #                 'company_id': self.env.user.company_id.id,
    #                 'group_id': group_id.id,
    #                 'branch_id': warehouse_id.branch_id.id,
    #                 'is_intra_com': True,
    #                 'src_warehouse_id': warehouse_id.id,
    #                 'dest_warehouse_id': des_warehouse_id[0].id,
    #                 'note': self.note
    #             }
    #         picking_id_1 = picking_obj.sudo().create(vals)
    #         picking_list.append(picking_id_1.id)
    #
    #         for line in product_line:
    #             move_list = []
    #             if warehouse_id.id == des_warehouse_id[0].id:
    #                 raise UserError("Source and destination warehouse should not be different for product %s" % (
    #                     line.product_id.name_get()[0][1]))
    #             if line.is_core_product:
    #                 move_vals = {
    #                     'name': (picking_id_1.name or '')[:2000],
    #                     'product_id': line.product_id.id,
    #                     'product_uom': line.product_id.uom_id.id,
    #                     'product_uom_qty': line.qty_transfer,
    #                     'date': sched_date_val,
    #                     'location_id': line.core_location_id.id,
    #                     'location_dest_id': transit_location_id.id,
    #                     'picking_id': picking_id_1.id,
    #                     'company_id': self.env.user.company_id.id,
    #                     'picking_type_id': warehouse_id.int_type_id.id,
    #                     'group_id': group_id.id,
    #                     'origin': picking_id_1.name,
    #                     'warehouse_id': warehouse_id.id,
    #                     'branch_id': line.warehouse_id.branch_id.id,
    #                     'move_options': line.quant_action if line.quant_action else 'new_product',
    #                     'src_warehouse_id': warehouse_id.id,
    #                     'dest_warehouse_id': des_warehouse_id[0].id,
    #                     'note': line.notes,
    #
    #                 }
    #                 move_list.append(move_vals)
    #                 move_1 = move_obj.sudo().create(move_list)
    #                 src_list.append(move_1.id)
    #             else:
    #                 move_vals = {
    #                     'name': (picking_id_1.name or '')[:2000],
    #                     'product_id': line.product_id.id,
    #                     'product_uom': line.product_id.uom_id.id,
    #                     'product_uom_qty': line.qty_transfer,
    #                     'date': sched_date_val,
    #                     'location_id': line.warehouse_id.lot_stock_id.id,
    #                     'location_dest_id': transit_location_id.id,
    #                     'picking_id': picking_id_1.id,
    #                     'company_id': self.env.user.company_id.id,
    #                     'picking_type_id': warehouse_id.int_type_id.id,
    #                     'group_id': group_id.id,
    #                     'origin': picking_id_1.name,
    #                     'warehouse_id': warehouse_id.id,
    #                     'branch_id': line.warehouse_id.branch_id.id,
    #                     'move_options': line.quant_action if line.quant_action else 'new_product',
    #                     'src_warehouse_id': warehouse_id.id,
    #                     'dest_warehouse_id': des_warehouse_id[0].id,
    #                     'note': line.notes,
    #
    #                 }
    #                 move_list.append(move_vals)
    #                 move_1 = move_obj.sudo().create(move_list)
    #                 src_list.append(move_1.id)
    #                 move_list = []
    #                 if line.product_id.has_core:
    #                     product_id = self.env['product.product'].search(
    #                         [('product_tmpl_id', '=', line.product_id.core_product_id.id)])
    #                     move_vals = {
    #                         'name': (picking_id_1.name or '')[:2000],
    #                         'product_id': product_id.id,
    #                         'product_uom': product_id.uom_id.id,
    #                         'product_uom_qty': line.product_id.core_qty * line.qty_transfer,
    #                         'date': sched_date_val,
    #                         'location_id': line.warehouse_id.lot_stock_id.id,
    #                         'location_dest_id': transit_location_id.id,
    #                         'picking_id': picking_id_1.id,
    #                         'company_id': self.env.user.company_id.id,
    #                         'picking_type_id': warehouse_id.int_type_id.id,
    #                         'group_id': group_id.id,
    #                         'origin': picking_id_1.name,
    #                         'warehouse_id': warehouse_id.id,
    #                         'branch_id': line.warehouse_id.branch_id.id,
    #                         'move_options': line.quant_action if line.quant_action else 'new_product',
    #                         'sm_line_id': move_1.id,
    #                         'src_warehouse_id': warehouse_id.id,
    #                         'dest_warehouse_id': des_warehouse_id[0].id,
    #                     }
    #                     move_list.append(move_vals)
    #                     move_has_core = move_obj.sudo().create(move_list)
    #                     src_list.append(move_has_core.id)
    #
    #         # create in picking
    #         group_id = self.env['procurement.group'].sudo().create({
    #             'name': des_warehouse_id[0].name, 'move_type': 'one',
    #         })
    #         # receive_sched_id=self.env['trucks.schedule'].search([('location_id','=',line.des_warehouse_id.lot_stock_id.id),('receives_from_loc_ids','in',(line.warehouse_id.lot_stock_id.id))],limit=1)
    #         # if receive_sched_id:
    #         #     todayDate = datetime.today()
    #         #     dateDay = {dt.strftime("%A"): dt for x in range(7) for dt in [sched_date_val + timedelta(x)]}
    #         #     sched_date_receive_val = dateDay[receive_sched_id.delivery_days]
    #         #     sched_date_val=sched_date_receive_val
    #         # else:
    #         #     sched_date_val = fields.Datetime.now()
    #
    #         i = 0
    #         receive_sched_id = self.env['trucks.schedule'].sudo().search(
    #             [('location_id', '=', line.des_warehouse_id.lot_stock_id.id),
    #              ('receives_from_loc_ids', 'in', (line.warehouse_id.lot_stock_id.id))])
    #         for truck_sche in receive_sched_id:
    #             if truck_sche:
    #                 todayDate = datetime.today()
    #                 dateDay = {dt.strftime("%A"): dt for x in range(7) for dt in [todayDate + timedelta(x)]}
    #                 sched_date_val = dateDay[truck_sche.delivery_days]
    #                 sche_receive_list.append(sched_date_val)
    #         if sche_receive_list:
    #             scheduledatelist = min(sche_receive_list)
    #             if scheduledatelist:
    #                 receive_sched_date_val = scheduledatelist
    #         else:
    #             receive_sched_date_val = fields.Datetime.now()
    #
    #         transit_location_id = self.env['stock.location'].search([
    #             ('usage', '=', 'transit'),
    #             ('active', '=', True),
    #         ], limit=1)
    #         from_warehouse_name = warehouse_id.name
    #         src_warehouse_id = warehouse_id
    #         warehouse_id = self.env['stock.warehouse'].browse(des_warehouse_id[0].id)
    #         vals = {
    #             'picking_type_id': des_warehouse_id[0].int_type_id.id,
    #             'date': receive_sched_date_val,
    #             'origin': 'Warehouse Inventory Transfer from %s' % (from_warehouse_name),
    #             'location_dest_id': des_warehouse_id[0].lot_stock_id.id,
    #             'location_id': transit_location_id.id,
    #             'company_id': self.env.user.company_id.id,
    #             'group_id': group_id.id,
    #             'branch_id': des_warehouse_id[0].branch_id.id,
    #             'prev_picking_id': picking_id_1.id,
    #             'is_intra_com': True,
    #             'src_warehouse_id': src_warehouse_id.id,
    #             'dest_warehouse_id': des_warehouse_id[0].id,
    #             'note': self.note
    #         }
    #         picking_id_2 = picking_obj.sudo().create(vals)
    #         picking_list.append(picking_id_2.id)
    #         move_list = []
    #         for line in product_line:
    #             move_vals = {
    #                 'name': (picking_id_2.name or '')[:2000],
    #                 'product_id': line.product_id.id,
    #                 'product_uom': line.product_id.uom_id.id,
    #                 'product_uom_qty': line.qty_transfer,
    #                 'date': receive_sched_date_val,
    #                 'location_id': transit_location_id.id,
    #                 'location_dest_id': line.des_warehouse_id.lot_stock_id.id,
    #                 'picking_id': picking_id_2.id,
    #                 'state': 'draft',
    #                 'company_id': self.env.user.company_id.id,
    #                 'picking_type_id': warehouse_id.int_type_id.id,
    #                 'group_id': group_id.id,
    #                 'origin': 'Warehouse Inventory Transfer to ' + line.des_warehouse_id.name,
    #                 'warehouse_id': warehouse_id.id,
    #                 'move_options': line.quant_action if line.quant_action else 'new_product',
    #                 'branch_id': des_warehouse_id[0].branch_id.id,
    #                 'src_warehouse_id': src_warehouse_id.id,
    #                 'dest_warehouse_id': des_warehouse_id[0].id,
    #                 'note': line.notes,
    #
    #             }
    #
    #             # move_ids=self.env['stock.move'].search([('picking_id','=',picking_id_1.id),('product_id','=',line.product_id.id),('location_id','=',line.warehouse_id.lot_stock_id.id)])
    #             if src_list:
    #                 move_vals.update({'move_orig_ids': [(6, 0, [src_list[i]])]})
    #                 i = i + 1
    #             move_list.append(move_vals)
    #             parent_move_id = move_obj.sudo().create(move_list)
    #             move_list = []
    #
    #             if line.product_id.has_core:
    #                 move_list = []
    #                 product_id = self.env['product.product'].search(
    #                     [('product_tmpl_id', '=', line.product_id.core_product_id.id)])
    #                 move_vals = {
    #                     'name': (picking_id_2.name or '')[:2000],
    #                     'product_id': product_id.id,
    #                     'product_uom': product_id.uom_id.id,
    #                     'product_uom_qty': line.product_id.core_qty * line.qty_transfer,
    #                     'date': receive_sched_date_val,
    #                     'location_id': transit_location_id.id,
    #                     'location_dest_id': line.des_warehouse_id.lot_stock_id.id,
    #                     'picking_id': picking_id_2.id,
    #                     'state': 'draft',
    #                     'company_id': self.env.user.company_id.id,
    #                     'picking_type_id': warehouse_id.int_type_id.id,
    #                     'group_id': group_id.id,
    #                     'origin': 'Warehouse Inventory Transfer to ' + line.des_warehouse_id.name,
    #                     'warehouse_id': warehouse_id.id,
    #                     'move_options': line.quant_action if line.quant_action else 'new_product',
    #                     'sm_line_id': parent_move_id.id,
    #                     'branch_id': des_warehouse_id[0].branch_id.id,
    #                     'src_warehouse_id': src_warehouse_id.id,
    #                     'dest_warehouse_id': des_warehouse_id[0].id,
    #
    #                 }
    #                 move_has_core = self.env['stock.move'].search(
    #                     [('picking_id', '=', picking_id_1.id), ('product_id', '=', product_id.id),
    #                      ('location_id', '=', warehouse_id.lot_stock_id.id)])
    #                 if src_list:
    #                     move_vals.update({'move_orig_ids': [(6, 0, [src_list[i]])]})
    #                     i = i + 1
    #                 move_list.append(move_vals)
    #                 move_obj.sudo().create(move_list)
    #                 move_list = []
    #         src_list = []
    #
    #         picking_id_1.sudo().action_confirm()
    #         picking_id_1.sudo().action_assign()
    #         picking_id_2.sudo().action_confirm()
    #         picking_id_1.update({
    #                                 'origin': 'Warehouse Inventory Transfer To ' + line.des_warehouse_id.name + ' ' + '[' + picking_id_2.name + ']'})
    #         picking_id_2.update({
    #                                 'origin': 'Warehouse Inventory Transfer From ' + line.warehouse_id.name + ' ' + '[' + picking_id_1.name + ']'})
    #         # for line in picking_id_1.move_ids_without_package_dummy:
    #         # for line in picking_id_1.move_ids_without_package:
    #         #     des_id = line.move_dest_ids.filtered(lambda r: r.product_id.id == line.product_id.id)
    #         #     pwi_id = self.env.cr.execute(
    #         #         """select id from product_warehouse_inventory where product_id=%s and warehouse_id=%s and company_id=%s""" % (
    #         #             line.product_id.id,des_id.picking_type_id.warehouse_id.id,
    #         #             line.picking_id.company_id.id))
    #         #     pwi_id = self.env.cr.fetchone()
    #         #     if pwi_id:
    #         #         pwi_id = pwi_obj.browse(pwi_id[0])
    #         #         pwi_id.write({
    #         #             'qty_on_order': pwi_id.qty_on_order+line.product_uom_qty,
    #         #         })
    #         #     pwi_reserve_id = self.env.cr.execute(
    #         #         """select id from product_warehouse_inventory where product_id=%s and warehouse_id=%s and company_id=%s""" % (
    #         #             line.product_id.id, line.picking_id.picking_type_id.warehouse_id.id,
    #         #             line.picking_id.company_id.id
    #         #         ))
    #         #     pwi_reserve_id = self.env.cr.fetchone()
    #         #     if pwi_reserve_id:
    #         #         pwi_reserve_id = pwi_obj.browse(pwi_reserve_id[0])
    #         #         pwi_reserve_id.write({
    #         #             'qty_reserve': pwi_reserve_id.qty_reserve + line.product_uom_qty,
    #         #         })
    #     return picking_list


class TransferPackageLine(models.TransientModel):
    _name = 'transfer.package.line'
    _description = 'Transfer Package Lines from Stock Quant.'



    transfer_package_id = fields.Many2one('transfer.package', string="Transfer")
    product_id = fields.Many2one('product.product', string="Product")
    quant_id = fields.Many2one('stock.quant', 'Stock Quant Id..')
    source_location_id = fields.Many2one('stock.location', 'Source Location')
    destination_location_id = fields.Many2one('stock.location', 'Destination Location')
    package_id = fields.Many2one('stock.quant.package', 'Source Package')
    result_package_id = fields.Many2one('stock.quant.package', 'Destination Package')
    qty_available = fields.Float(string="Onhand Quantity")
    qty_transfer = fields.Float(string="Qty To Transfer")
    company_id = fields.Many2one('res.company', 'Company')



    # @api.onchange('warehouse_id')
    # def _onchange_warehouse_id(self):
    #     for transfr_line in self:
    #         if self.warehouse_id:
    #             transfer_line_rec = self.env.cr.execute(
    #                 """select quantity from stock_quant where product_id=%s and warehouse_id=%s and company_id=%s""" % (
    #                     transfr_line.product_id.id, transfr_line.warehouse_id.id, transfr_line.warehouse_id.company_id.id))
    #             transfer_line_rec = self.env.cr.fetchall()
    #             transfr_line.qty_available = transfer_line_rec[0][0]if transfer_line_rec else 0

    @api.constrains('qty_transfer')
    def check_qty_transfer(self):
        for rec in self:
            if rec.qty_transfer < 0:
                raise ValidationError("Transfer quantity should be positive!")
            # if rec.qty_transfer > rec.qty_available:
            #     raise ValidationError("Transfer quantity should be less than available quantity for product %s"%(rec.product_id.name_get()[0][1]))

    # @api.onchange('qty_transfer')
    # def onchange_qty_transfer(self):
    #     product_uom_qty = self.qty_transfer
    #     product_uom = self.product_id.uom_id
    #     unit_categ = self.sudo().env.ref('uom.product_uom_categ_unit')
    #     if unit_categ == product_uom.category_id:
    #         if isinstance(product_uom_qty, float):
    #             if not product_uom_qty.is_integer():
    #                 raise UserError(_("Please enter correct Quantity!"))

