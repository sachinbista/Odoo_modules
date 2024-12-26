from odoo import models, fields, api, _


class AccountMove(models.Model):
    _inherit = "account.move"

    def _create_return_picking_from_credit_note(self, picking):
        context = dict(self.env.context)
        context.update({
            'active_id': picking.id,
            'active_model': 'stock.picking',
        })
        return_wizard = self.env['stock.return.picking'].with_context(context).create({
            'picking_id': picking.id,
        })
        for return_line in return_wizard.product_return_moves:
            for move_line in self.invoice_line_ids:
                if return_line.product_id == move_line.product_id:
                    return_line.quantity = move_line.quantity

        if self.move_type == 'out_refund':
            new_picking_id, pick_type_id = return_wizard._create_returns()
            new_picking = self.env['stock.picking'].browse(new_picking_id)

            # if new_picking:
            #     new_picking.button_validate()
            self.picking_ids = [(4, new_picking.id)]

    def _reverse_moves(self, default_values_list=None, cancel=False):
        res = super()._reverse_moves(default_values_list=default_values_list, cancel=cancel)
        picking_ids = self.picking_ids.filtered(lambda p:p.state == 'done')
        if picking_ids:
            res._create_return_picking_from_credit_note(picking_ids)
        return res


    def action_post(self):
        if self._context.get('no_check',False):
            res =  super().action_post()
            self.reconcile_delivery()
            if self.picking_ids:
                self.picking_ids.origin = self.name
            return res
        for move in self:
            credit_limit_manager = self.env.user.has_group('bista_customer_credit_limit.customer_credit_limit_manager')
            if move.partner_id.credit_check and not credit_limit_manager:
                sale_value = sum(line.price_subtotal for line in self.invoice_line_ids)
                total_due = move.partner_id.total_due + sale_value
                if move.partner_id.credit_blocking < total_due:
                    return {
                        'name': _('Credit Limit'),
                        'type': 'ir.actions.act_window',
                        'res_model': 'credit.limit.wizard',
                        'view_id': self.env.ref('bista_customer_credit_limit.credit_limit_wizard_view_form').id,
                        'view_mode': 'form',
                        'target': 'new',
                        'context': {
                            'default_name': 'Customer credit limit exceeded.'
                        },
                    }
            # if move.move_type == 'out_refund' and move.reversed_entry_id:
            #     for org_move in move.reversed_entry_id:
            #         for picking in org_move.picking_ids:
            #             if picking.state == 'done':
            #                 self._create_return_picking_from_credit_note(picking)
            if self.company_id.is_delivery_invoice and self.move_type == 'out_invoice':
                picking_action = self.create_picking()
                if isinstance(picking_action, dict):
                    return picking_action
        res  = super().action_post()
        self.reconcile_delivery()
        if self.picking_ids:
            self.picking_ids.origin = self.name
        return res

    def reconcile_delivery(self):
        stock_out_account = False
        for line in self.invoice_line_ids:
            if not stock_out_account:
                stock_out_account = line.product_id.categ_id.property_stock_account_output_categ_id
            move_line = self.line_ids.filtered(lambda l: l.account_id == stock_out_account and l.product_id == line.product_id)
            svl_id = (self.picking_ids.move_ids).stock_valuation_layer_ids.filtered(lambda l: l.product_id == line.product_id)
            if svl_id:
                svl_move_line = svl_id.account_move_id.line_ids.filtered(lambda l: l.account_id == stock_out_account)
                if move_line and svl_move_line and move_line.parent_state == 'posted' and svl_move_line.parent_state == 'posted':
                    (svl_move_line + move_line).reconcile()


    def create_picking(self):
        """
        Check stock before confirming delivery. If insufficient stock, pop the wizard.
        """
        insufficient_stock = False
        insufficient_products = []

        # warehouse = self.env['stock.warehouse'].search([('company_id', '=', self.company_id.id)], limit=1)
        warehouse = self.company_id.warehouse_id
        stock_location = warehouse.lot_stock_id
        if not self._context.get('insufficient_stock_skip', False):
            for line in self.invoice_line_ids:
                if line.product_id and line.product_id.type == 'product':
                    stock_quant = self.env['stock.quant'].search([
                        ('product_id', '=', line.product_id.id),
                        ('location_id', '=', stock_location.id)
                    ])
                    available_qty = sum(stock_quant.mapped('quantity'))

                    if line.quantity > available_qty:
                        insufficient_stock = True
                        insufficient_products.append(
                            f"{line.product_id.display_name} (Available: {available_qty}, Needed: {line.quantity})")

            if insufficient_stock:
                    product_list = '\n'.join(insufficient_products)
                    return {
                        'name': _('Insufficient Stock'),
                        'view_mode': 'form',
                        'res_model': 'insufficient.stock.wizard',
                        'view_id': self.env.ref('bista_delivery_return_from_inv.insufficient_stock_wizard_view_form').id,
                        'type': 'ir.actions.act_window',
                        'target': 'new',
                        'context': {
                        'active_id': self.id,
                        'insufficient_products': product_list,
                    },
                    }
        self.invoice_line_ids._action_launch_stock_rule()
        return True


    def _create_picking_with_invoice_qty(self):
        """
        Create the stock picking using the quantities from the invoice.
        """
        self.invoice_line_ids.with_context(skip_sanity_check=True)._action_launch_stock_rule()
        # picking = self._context.get('picking_id')
        # move = self._context.get('active_id')
        # if move:
        #     move_id = self.env['account.move'].browse(move)
        #     move_id.action_post()
        # if picking:
        #     picking_id = self.env['stock.picking'].browse(picking)
        #     if not self.env.context.get('skip_sanity_check', False):
        #         picking_id._sanity_check()
        #     picking_id.message_subscribe([self.env.user.partner_id.id])
        #     res = picking_id._pre_action_done_hook()
        #     if res is not True:
        #         return res
        #     picking_id.with_context(cancel_backorder=False)._action_done()





    # def action_reverse(self):
    #     res = super().action_reverse()
    #
    #     for move in self:
    #         if move.picking_ids:
    #             for picking in move.picking_ids:
    #                 if picking.state == 'done':
    #                     self._create_return_picking_from_credit_note(picking)
    #
    #     return res
    #
    # def _create_return_picking_from_credit_note(self, picking):
    #     context = dict(self.env.context)
    #     context.update({
    #         'active_id': picking.id,
    #         'active_model': 'stock.picking',
    #     })
    #     return_wizard = self.env['stock.return.picking'].with_context(context).create({
    #         'picking_id': picking.id,
    #     })
    #     # return_wizard.create_returns()
    #     new_picking_id, pick_type_id = return_wizard._create_returns()
    #
    #     new_picking = self.env['stock.picking'].browse(new_picking_id)
    #     if new_picking:
    #         new_picking.button_validate()
    #
    #     return new_picking_id
    #
    # def action_post(self):
    #     res = super().action_post()
    #     for move in self:
    #         if move.move_type == 'out_refund':
    #             if move.picking_ids:
    #                 for picking in move.picking_ids:
    #                     if picking.state == 'done':
    #                         print("pickingggggggggg",picking)
    #                         self._create_return_picking_from_credit_note(picking)
    #
    #     return res