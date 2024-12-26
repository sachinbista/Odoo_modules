from odoo import models, fields, api, _



class InsufficientStockWizard(models.TransientModel):
    _name = 'insufficient.stock.wizard'
    _description = 'Insufficient Stock Wizard'

    insufficient_products = fields.Text(string="Insufficient Products", readonly=True)

    @api.model
    def default_get(self, fields):

        res = super(InsufficientStockWizard, self).default_get(fields)
        insufficient_products = self.env.context.get('insufficient_products')
        if insufficient_products:
            res.update({
                'insufficient_products': insufficient_products
            })
        return res

    def action_proceed(self):
        context = self.env.context
        move_id = self.env['account.move'].browse(context.get('active_id'))
        if move_id:
            move_id._create_picking_with_invoice_qty()
            move_id.with_context(no_check=True).action_post()
        return True

    def action_cancel(self):
        context = self.env.context
        move_id = self.env['account.move'].browse(context.get('active_id'))
        if move_id and not move_id.state =='draft':
            move_id.button_draft()
        return {'type': 'ir.actions.act_window_close'}
