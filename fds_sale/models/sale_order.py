import logging
from odoo import fields, models, api, _
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    state = fields.Selection(
        selection=[
            ('draft', "Quotation"),
            ('sent', "Quotation Sent"),
            ('committed', "Preliminary Quotation"),
            ('sale', "Sales Order"),
            ('done', "Locked"),
            ('cancel', "Cancelled"),
        ],
        string="Status",
        readonly=True, copy=False, index=True,
        tracking=3,
        default='draft')
    client_order_ref = fields.Char(string='Purchase Order', copy=False)
    can_prelim = fields.Char(string='Can Prelim ?', compute='_compute_can_prelim')

    def _compute_can_prelim(self):
        partner_can_commit_quotation = self.env.user.partner_id.can_commit_quotation
        for rec in self:
            rec.can_prelim = partner_can_commit_quotation and (rec.state in ('draft', 'sent'))

    @api.depends('state')
    def _compute_type_name(self):
        for record in self:
            if record.state in ('draft'):
                record.type_name = _("Estimate")
            elif record.state in ('sent', 'cancel'):
                record.type_name = _("Quotation")
            elif record.state == 'committed':
                record.type_name = _("Preliminary Quotation")
            else:
                record.type_name = _("Sales Order")

    def action_commit(self):
        """Commit the quotation."""
        self.write(self._prepare_commitment_values())
        self._action_commit()
        return True

    def _action_commit(self):
        if self._allow_create_committed_transfer():
            self.order_line._action_launch_committed_transfer()
        else:
            self.message_post(body=_("<li><font style='color:Orange;'>Warehouse <strong>%s</strong> is not allowed for committed quotes.</font></li>", self.warehouse_id.name))
        return True
    
    def _allow_create_committed_transfer(self):
        self.ensure_one()
        return self.warehouse_id.commit_type_id

    
    def _prepare_commitment_values(self):
        """Prepare the sales order commitment values."""
        return {
            'state': 'committed'
        }
    
    def _action_confirm(self):
        """Cancel Delivery Committed Orders.
        """
        for order in self:
            type_committed_order = order.warehouse_id.commit_type_id
            committed_orders = order.picking_ids.filtered(lambda p: p.picking_type_id == type_committed_order)
            committed_orders.action_cancel()
        return super(SaleOrder, self)._action_confirm()

    def get_do_pick_status(self):
        do_outs = self.picking_ids.filtered(lambda p: p.picking_type_id == self.warehouse_id.out_type_id)
        state = 'N/A'
        if do_outs:
            if len(do_outs) > 1:
                if all(do.state == 'done' for do in do_outs):
                    # All DO are done
                    do_outs = do_outs[0]
                else:
                    # There is a backorder not done
                    do_outs = do_outs.filtered(lambda d: d.state != 'done')
            if do_outs.state == 'assigned' and do_outs.show_check_availability:
                state = '<span class="badge badge-pill badge-info">Partial</span>'
            else:
                mapping = {
                    'assigned': '<span class="badge badge-pill badge-info">Ready</span>',
                    'done': '<span class="badge badge-pill badge-success">Done</span>'
                }
                state = mapping.get(do_outs.state, '<span class="badge badge-pill badge-light">Waiting</span>')
        return state

    
    def action_cancel(self):
        """Prevent a confirmed Sales Order from being canceled.
         
        If:
        - picking is started or is done.
        OR
        - manufacturing has been started done
        """
        self._check_picking_status()
        self._check_mo_status()
        return super(SaleOrder, self).action_cancel()

    # def _check_picking_status(self):
    #     type_committed_order = self.warehouse_id.commit_type_id
    #     delivery_pickings = self.picking_ids.filtered(lambda p: p.picking_type_id != type_committed_order)
    #     if any((p.state in ('assigned', 'done') for p in delivery_pickings)):
    #         raise ValidationError(_("You can't cancel Sale Order when Delivery was started or done."))

    def _check_picking_status(self):
        """Prevent cancellation if any delivery is started or done, unless conditions are met."""
        # type_committed_order = self.warehouse_id.commit_type_id
        # delivery_pickings = self.picking_ids.filtered(lambda p: p.picking_type_id != type_committed_order)
        user_is_inventory_manager = self.env.user.has_group('stock.group_stock_manager')
        for order in self:
            # if picking.state in ('assigned', 'done'):
            total_delivered_qty = sum(line.qty_delivered for line in order.order_line)
            if total_delivered_qty > 0:
                    raise ValidationError(
                        _("You can't cancel Sale Order when Delivery was started or done."))
            else:
                if not user_is_inventory_manager:
                    raise ValidationError(
                        _("You can't cancel Sale Order when Delivery was started or done.")
                    )


    def _check_mo_status(self):
        """Check if any MO is in progress or done"""
        check_state = ('progress', 'to_close', 'done')
        for mo in self.mrp_production_ids:
            if mo.state in check_state:
                raise ValidationError(_("You can't cancel Sale Order when Manufacturing Orders was started or done."))

    # PORTAL #
    def _has_to_be_signed(self, include_draft=False):
        result = super(SaleOrder, self)._has_to_be_signed()
        if self.state == 'draft':
            result = False
        return result
    
    def _has_to_be_paid(self, include_draft=False):
        result = super(SaleOrder, self)._has_to_be_paid()
        if self.state == 'draft':
            result = False
        return result
