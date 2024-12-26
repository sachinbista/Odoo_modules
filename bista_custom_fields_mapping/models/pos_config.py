from odoo import api, fields, models
from odoo.exceptions import Warning,ValidationError


class pos_config(models.Model):
    _inherit = 'pos.config'

    image = fields.Binary("Image")
    disc_pwd = fields.Integer(string='Password')
    allowed_disc = fields.Float(string='Allowed Discount')
    wk_display_stock = fields.Boolean('Display stock in POS', default=True)
    wk_stock_type = fields.Selection(
        [('available_qty', 'Available Quantity(On hand)'), ('forecasted_qty', 'Forecasted Quantity'),
         ('virtual_qty', 'Quantity on Hand - Outgoing Qty')], string='Stock Type', default='available_qty')
    wk_continous_sale = fields.Boolean('Allow Order When Out-of-Stock')
    wk_deny_val = fields.Integer('Deny order when product stock is lower than ')
    wk_error_msg = fields.Char(string='Custom message', default="Product out of stock")
    wk_hide_out_of_stock = fields.Boolean(string="Hide Out of Stock products", default=True)
    order_loading_options = fields.Selection(
        [("current_session", "Load Orders Of Current Session"), ("all_orders", "Load All Past Orders"),
         ("n_days", "Load Orders Of Last 'n' Days")], default='current_session', string="Loading Options")
    number_of_days = fields.Integer(string='Number Of Past Days', default=10)
    wk_reprint_type = fields.Selection([('posbox', 'POSBOX(Xml Report)'),
                                        ('ticket', 'Pos Ticket (Order Receipt)'),
                                        ('pdf', 'Browser Based (Pdf Report)')
                                        ], default='ticket', required=True, string='Order Reprint Type')

    # @api.one
    @api.constrains('wk_reprint_type', 'iface_print_via_proxy')
    def check_wk_reprint_type(self):
        if (self.wk_reprint_type == 'posbox'):
            if (self.iface_print_via_proxy == False):
                raise ValidationError(
                    "You can not print Xml Report unless you configure the Receipt Printer settings under Hardware Proxy/PosBox!!!")

    @api.constrains('number_of_days')
    def number_of_days_validation(self):
        if self.order_loading_options == 'n_days':
            if not self.number_of_days or self.number_of_days < 0:
                raise ValidationError("Please provide a valid value for the field 'Number Of Past Days'!!!")

    @api.model
    def wk_pos_fetch_pos_stock(self, kwargs):
        result = {}
        location_id = False
        wk_stock_type = kwargs['wk_stock_type']
        wk_hide_out_of_stock = kwargs['wk_stock_type']
        config_id = self.browse([kwargs.get('config_id')])
        picking_type = config_id.picking_type_id
        location_id = picking_type.default_location_src_id.id
        product_obj = self.env['product.product']
        pos_products = product_obj.search([('sale_ok', '=', True), ('available_in_pos', '=', True)])
        pos_products_qtys = pos_products.with_context(location=location_id)._product_available()
        for pos_product in pos_products_qtys:
            if wk_stock_type == 'available_qty':
                result[pos_product] = pos_products_qtys[
                    pos_product]['qty_available']
            elif wk_stock_type == 'forecasted_qty':
                result[pos_product] = pos_products_qtys[
                    pos_product]['virtual_available']
            else:
                result[pos_product] = pos_products_qtys[pos_product][
                                          'qty_available'] - pos_products_qtys[pos_product]['outgoing_qty']
        return result

class PosOrder(models.Model):
    _inherit = 'pos.order'

    order_tax_id = fields.Char(string='Tax Id')
    is_return_order = fields.Boolean(string='Return Order', copy=False)
    return_order_id = fields.Many2one('pos.order', 'Return Order Of', readonly=True, copy=False)
    return_status = fields.Selection(
        [('-', 'Not Returned'), ('Fully-Returned', 'Fully-Returned'), ('Partially-Returned', 'Partially-Returned'),
         ('Non-Returnable', 'Non-Returnable')], default='-', copy=False, string='Return Status')

    is_tax_free_order = fields.Boolean("Is Tax free order?", default=False)
    other_users = fields.Many2many(string='Other Salesperson', comodel_name='res.users')
    users_count = fields.Integer(compute='_compute_user_count', store=True)

    @api.model
    def _order_fields(self, ui_order):
        fields_return = super(PosOrder, self)._order_fields(ui_order)
        other_users = ui_order.get('other_users', [])
        fields_return.update({'order_tax_id': ui_order.get('order_tax_id', ''), 'other_users': other_users})
        return fields_return

    @api.depends('user_id', 'other_users')
    def _compute_user_count(self):
        for rec in self:
            if rec.other_users or rec.user_id:
                rec.users_count = len(rec.other_users.filtered(lambda x: x.active == True)) + len(rec.user_id)

    # @api.model
    # def _order_fields(self, ui_order):
    #     fields_return = super(PosOrder, self)._order_fields(ui_order)
    #     other_users = ui_order.get('other_users', [])
    #     fields_return.update({'order_tax_id': ui_order.get('order_tax_id', ''), 'other_users': other_users})
    #     return fields_return


class pos_order_line(models.Model):
    _inherit = 'pos.order.line'

    sku_number = fields.Char(string='SKU Number', related='product_id.default_code')
    line_qty_returned = fields.Integer('Line Returned', default=0)
    original_line_id = fields.Many2one('pos.order.line', "Original line")
    cost_price = fields.Float(string='Cost', compute='get_service_cost_price')
    order_line_note = fields.Text('Extra Comments')

    def get_service_cost_price(self):
        for res in self:
            if res.product_id.type == 'service' and res.product_id.categ_id.sale_type == 'repair':
                res.cost_price = res.price_subtotal * .70
            else:
                res.cost_price = res.product_id.standard_price or 0.0
        return True

    @api.model
    def _order_line_fields(self, line, session_id=None):
        fields_return = super(pos_order_line, self)._order_line_fields(line, session_id)
        fields_return[2].update({'line_qty_returned': line[2].get('line_qty_returned', '')})
        fields_return[2].update({'original_line_id': line[2].get('original_line_id', '')})
        return fields_return

class PosPaymentMethod(models.Model):
    _inherit = 'pos.payment.method'

    cash_journal_id = fields.Many2one('account.journal',
        string='Cash/Bank Journal',
        domain=[('type', 'in', ('cash','bank'))],
        ondelete='restrict',
        help='The payment method is of type cash. A cash statement will be automatically generated.')

    is_cash_count = fields.Boolean(string='Cash/Bank')