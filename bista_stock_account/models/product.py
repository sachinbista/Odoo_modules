from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools import float_is_zero, float_repr, float_round, float_compare
from odoo.exceptions import ValidationError
from collections import defaultdict


class ProductProduct(models.Model):
    _inherit = 'product.product'

    def _change_standard_price(self, new_price):
        """Helper to create the stock valuation layers and the account moves
        after an update of standard price.

        :param new_price: new standard price
        """
        # Handle stock valuation layers.

        if self.filtered(lambda p: p.valuation == 'real_time') and not self.env[
            'stock.valuation.layer'].check_access_rights('read', raise_exception=False):
            raise UserError(
                _("You cannot update the cost of a product in automated valuation as it leads to the creation of a journal entry, for which you don't have the access rights."))

        svl_vals_list = []
        company_id = self.env.company
        price_unit_prec = self.env['decimal.precision'].precision_get('Product Price')
        rounded_new_price = float_round(new_price, precision_digits=price_unit_prec)
        stock_valuation_layers = self.env['stock.valuation.layer']
        for product in self:
            if product.cost_method not in ('standard', 'average'):
                continue
            quantity_svl = product.sudo().quantity_svl
            if float_compare(quantity_svl, 0.0, precision_rounding=product.uom_id.rounding) <= 0:
                continue
            value_svl = product.sudo().value_svl
            value = company_id.currency_id.round((rounded_new_price * quantity_svl) - value_svl)
            if company_id.currency_id.is_zero(value):
                continue

            svl_vals = {
                'company_id': company_id.id,
                'product_id': product.id,
                'description': _('Product value manually modified (from %s to %s)') % (
                product.standard_price, rounded_new_price),
                'value': value,
                'quantity': 0,
            }
            svl_vals_list.append(svl_vals)
        if svl_vals_list:
            stock_valuation_layers = self.env['stock.valuation.layer'].sudo().create(svl_vals_list)

        # Handle account moves.
        product_accounts = {product.id: product.product_tmpl_id.get_product_accounts() for product in self}
        am_vals_list = []
        if stock_valuation_layers:
            for stock_valuation_layer in stock_valuation_layers:
                product = stock_valuation_layer.product_id
                value = stock_valuation_layer.value

                if product.type != 'product' or product.valuation != 'real_time':
                    continue

                # Sanity check.
                if not product_accounts[product.id].get('expense'):
                    raise UserError(_('You must set a counterpart account on your product category.'))
                if not product_accounts[product.id].get('stock_valuation'):
                    raise UserError(
                        _('You don\'t have any stock valuation account defined on your product category. You must define one before processing this operation.'))

                if value < 0:
                    debit_account_id = product_accounts[product.id]['expense'].id
                    credit_account_id = product_accounts[product.id]['stock_valuation'].id
                else:
                    debit_account_id = product_accounts[product.id]['stock_valuation'].id
                    credit_account_id = product_accounts[product.id]['expense'].id

                move_vals = {
                    'journal_id': product_accounts[product.id]['stock_journal'].id,
                    'company_id': company_id.id,
                    'ref': product.default_code,
                    'stock_valuation_layer_ids': [(6, None, [stock_valuation_layer.id])],
                    'move_type': 'entry',
                    'line_ids': [(0, 0, {
                        'name': _(
                            '%(user)s changed cost from %(previous)s to %(new_price)s - %(product)s',
                            user=self.env.user.name,
                            previous=product.standard_price,
                            new_price=new_price,
                            product=product.display_name
                        ),
                        'account_id': debit_account_id,
                        'debit': abs(value),
                        'credit': 0,
                        'product_id': product.id,
                    }), (0, 0, {
                        'name': _(
                            '%(user)s changed cost from %(previous)s to %(new_price)s - %(product)s',
                            user=self.env.user.name,
                            previous=product.standard_price,
                            new_price=new_price,
                            product=product.display_name
                        ),
                        'account_id': credit_account_id,
                        'debit': 0,
                        'credit': abs(value),
                        'product_id': product.id,
                    })],
                }
                am_vals_list.append(move_vals)

            account_moves = self.env['account.move'].sudo().create(am_vals_list)
            if account_moves:
                account_moves._post()

    @api.model
    def _svl_empty_stock_am(self, stock_valuation_layers):
        move_vals_list = []
        if stock_valuation_layers:
            product_accounts = {product.id: product.product_tmpl_id.get_product_accounts() for product in stock_valuation_layers.mapped('product_id')}
            for out_stock_valuation_layer in stock_valuation_layers:
                product = out_stock_valuation_layer.product_id
                stock_input_account = product_accounts[product.id].get('stock_input')
                if not stock_input_account:
                    raise UserError(_('You don\'t have any stock input account defined on your product category. You must define one before processing this operation.'))
                if not product_accounts[product.id].get('stock_valuation'):
                    raise UserError(_('You don\'t have any stock valuation account defined on your product category. You must define one before processing this operation.'))

                debit_account_id = stock_input_account.id
                credit_account_id = product_accounts[product.id]['stock_valuation'].id
                value = out_stock_valuation_layer.value
                move_vals = {
                    'journal_id': product_accounts[product.id]['stock_journal'].id,
                    'company_id': self.env.company.id,
                    'ref': product.default_code,
                    'stock_valuation_layer_ids': [(6, None, [out_stock_valuation_layer.id])],
                    'line_ids': [(0, 0, {
                        'name': out_stock_valuation_layer.description,
                        'account_id': debit_account_id,
                        'debit': abs(value),
                        'credit': 0,
                        'product_id': product.id,
                    }), (0, 0, {
                        'name': out_stock_valuation_layer.description,
                        'account_id': credit_account_id,
                        'debit': 0,
                        'credit': abs(value),
                        'product_id': product.id,
                    })],
                    'move_type': 'entry',
                }
                move_vals_list.append(move_vals)
        return move_vals_list

    def _svl_replenish_stock_am(self, stock_valuation_layers):
        move_vals_list = []
        if stock_valuation_layers:
            product_accounts = {product.id: product.product_tmpl_id.get_product_accounts() for product in stock_valuation_layers.mapped('product_id')}
            for out_stock_valuation_layer in stock_valuation_layers:
                product = out_stock_valuation_layer.product_id
                if not product_accounts[product.id].get('stock_input'):
                    raise UserError(_('You don\'t have any input valuation account defined on your product category. You must define one before processing this operation.'))
                if not product_accounts[product.id].get('stock_valuation'):
                    raise UserError(_('You don\'t have any stock valuation account defined on your product category. You must define one before processing this operation.'))

                debit_account_id = product_accounts[product.id]['stock_valuation'].id
                credit_account_id = product_accounts[product.id]['stock_input'].id
                value = out_stock_valuation_layer.value
                move_vals = {
                    'journal_id': product_accounts[product.id]['stock_journal'].id,
                    'company_id': self.env.company.id,
                    'ref': product.default_code,
                    'stock_valuation_layer_ids': [(6, None, [out_stock_valuation_layer.id])],
                    'line_ids': [(0, 0, {
                        'name': out_stock_valuation_layer.description,
                        'account_id': debit_account_id,
                        'debit': abs(value),
                        'credit': 0,
                        'product_id': product.id,
                    }), (0, 0, {
                        'name': out_stock_valuation_layer.description,
                        'account_id': credit_account_id,
                        'debit': 0,
                        'credit': abs(value),
                        'product_id': product.id,
                    })],
                    'move_type': 'entry',
                }
                move_vals_list.append(move_vals)
        return move_vals_list
