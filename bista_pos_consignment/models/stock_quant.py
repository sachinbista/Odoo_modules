# -*- encoding: utf-8 -*-
##############################################################################
#
#    Bista Solutions Pvt. Ltd
#    Copyright (C) 2016 (http://www.bistasolutions.com)
#
##############################################################################
from collections import defaultdict
from datetime import timedelta
from operator import itemgetter

from odoo import _, api, Command, fields, models
from odoo.exceptions import UserError
from odoo.osv import expression
from odoo.tools.float_utils import float_compare, float_is_zero, float_round



class StockQuant(models.Model):
    _inherit = "stock.quant"

    @api.model
    def _get_available_quantity(self, product_id, location_id, lot_id=None, package_id=None, owner_id=None,
                                strict=False, allow_negative=False):
        if 'owner_value' in self._context:
            self = self.sudo()
            quants = self.with_context({'owner_value': True})._gather(product_id, location_id, lot_id=lot_id, package_id=package_id, owner_id=owner_id,
                                  strict=strict)
            rounding = product_id.uom_id.rounding
            if product_id.tracking == 'none':
                available_quantity = sum(quants.mapped('quantity')) - sum(quants.mapped('reserved_quantity'))
                if allow_negative:
                    return available_quantity
                else:
                    return available_quantity if float_compare(available_quantity, 0.0,
                                                               precision_rounding=rounding) >= 0.0 else 0.0
            else:
                availaible_quantities = {lot_id: 0.0 for lot_id in list(set(quants.mapped('lot_id'))) + ['untracked']}
                for quant in quants:
                    if not quant.lot_id:
                        availaible_quantities['untracked'] += quant.quantity - quant.reserved_quantity
                    else:
                        availaible_quantities[quant.lot_id] += quant.quantity - quant.reserved_quantity
                if allow_negative:
                    return sum(availaible_quantities.values())
                else:
                    return sum([available_quantity for available_quantity in availaible_quantities.values() if
                                float_compare(available_quantity, 0, precision_rounding=rounding) > 0])
        return super(StockQuant,self)._get_available_quantity(product_id, location_id, lot_id, package_id, owner_id,
                                strict,allow_negative)


    def _update_reserved_quantity(self, product_id, location_id, quantity, lot_id=None, package_id=None, owner_id=None, strict=False):
        if 'owner_value' in self._context:
            self = self.sudo()
            rounding = product_id.uom_id.rounding

            quants = self.with_context({'owner_value': True})._gather(product_id, location_id, lot_id=lot_id, package_id=package_id, owner_id=owner_id, strict=strict)
            reserved_quants = []

            if float_compare(quantity, 0, precision_rounding=rounding) > 0:
                # if we want to reserve
                available_quantity = sum(quants.filtered(lambda q: float_compare(q.quantity, 0, precision_rounding=rounding) > 0).mapped('quantity')) - sum(quants.mapped('reserved_quantity'))
                if float_compare(quantity, available_quantity, precision_rounding=rounding) > 0:
                    raise UserError(_('It is not possible to reserve more products of %s than you have in stock.', product_id.display_name))
            elif float_compare(quantity, 0, precision_rounding=rounding) < 0:
                # if we want to unreserve
                available_quantity = sum(quants.mapped('reserved_quantity'))
                if float_compare(abs(quantity), available_quantity, precision_rounding=rounding) > 0:
                    raise UserError(_('It is not possible to unreserve more products of %s than you have in stock.', product_id.display_name))
            else:
                return reserved_quants

            for quant in quants:
                if float_compare(quantity, 0, precision_rounding=rounding) > 0:
                    max_quantity_on_quant = quant.quantity - quant.reserved_quantity
                    if float_compare(max_quantity_on_quant, 0, precision_rounding=rounding) <= 0:
                        continue
                    max_quantity_on_quant = min(max_quantity_on_quant, quantity)
                    quant.reserved_quantity += max_quantity_on_quant
                    reserved_quants.append((quant, max_quantity_on_quant))
                    quantity -= max_quantity_on_quant
                    available_quantity -= max_quantity_on_quant
                else:
                    max_quantity_on_quant = min(quant.reserved_quantity, abs(quantity))
                    quant.reserved_quantity -= max_quantity_on_quant
                    reserved_quants.append((quant, -max_quantity_on_quant))
                    quantity += max_quantity_on_quant
                    available_quantity += max_quantity_on_quant

                if float_is_zero(quantity, precision_rounding=rounding) or float_is_zero(available_quantity, precision_rounding=rounding):
                    break
            return reserved_quants
        return super()._update_reserved_quantity( product_id, location_id, quantity, lot_id, package_id, owner_id, strict)

    def _gather(self, product_id, location_id, lot_id=None, package_id=None, owner_id=None, strict=False):
        removal_strategy = self._get_removal_strategy(product_id, location_id)
        removal_strategy_order = self._get_removal_strategy_order(removal_strategy)
        if 'owner_value' in self._context:
            domain = self.with_context({'owner_value':True})._get_gather_domain(product_id, location_id, lot_id, package_id, owner_id, strict)
        else:
            domain = self._get_gather_domain(product_id, location_id, lot_id, package_id, owner_id, strict)

        return self.search(domain, order=removal_strategy_order).sorted(lambda q: not q.lot_id)

    def _get_gather_domain(self, product_id, location_id, lot_id=None, package_id=None, owner_id=None, strict=False):
        domain = [('product_id', '=', product_id.id)]
        if not strict:
            if lot_id:
                domain = expression.AND([['|', ('lot_id', '=', lot_id.id), ('lot_id', '=', False)], domain])
            if package_id:
                domain = expression.AND([[('package_id', '=', package_id.id)], domain])
            if owner_id:
                domain = expression.AND([[('owner_id', '=', owner_id.id)], domain])
            domain = expression.AND([[('location_id', 'child_of', location_id.id)], domain])
        else:
            domain = expression.AND(
                [['|', ('lot_id', '=', lot_id.id), ('lot_id', '=', False)] if lot_id else [('lot_id', '=', False)],
                 domain])
            domain = expression.AND([[('package_id', '=', package_id and package_id.id or False)], domain])
            domain = expression.AND([[('owner_id', '=', owner_id and owner_id.id or False)], domain])
            domain = expression.AND([[('location_id', '=', location_id.id)], domain])
        if 'owner_value' in self._context:
            domain = expression.AND([[('owner_id', '!=', False)], domain])
        return domain

