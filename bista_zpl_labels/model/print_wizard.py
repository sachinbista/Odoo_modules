from odoo import models, fields, api
from odoo.exceptions import UserError


class PrintWizard(models.TransientModel):
    _name = "print.wizard"
    _description = "Print Wizard"

    name = fields.Many2one('zpl.label', string="Label")
    printer = fields.Char()
    model_id = fields.Many2one('ir.model')
    model = fields.Selection([
        ('product.template', 'Product'),
        ('stock.lot', 'Lot/Serial'),
        ('stock.quant', 'Stock Quant'),
        ('stock.location', 'Location'),
        ('stock.picking', 'Stock Picking')], default="product.template")
    product_ids = fields.Many2many('product.template')
    lot_ids = fields.Many2many('stock.lot')
    picking_ids = fields.Many2many('stock.picking')

    quant_ids = fields.Many2many('stock.quant')
    location_ids = fields.Many2many('stock.location')

    label_count = fields.Integer(string="Number of Labels", compute="_get_label_count")
    print_count_ids = fields.One2many('print.wizard.print_count', 'print_wizard_id')
    copies = fields.Integer(default=1)

    product_label = fields.Many2one('zpl.label')
    lot_label = fields.Many2one('zpl.label')

    @api.onchange("name")
    def _get_label_types(self):
        if not self.name:
            return
        if self.model == 'stock.picking':
            self.product_label = self.name.product_label
            self.lot_label = self.name.lot_label
        elif self.model == 'product.template':
            self.product_label = self.name.id
        elif self.model == 'stock.lot':
            self.lot_label = self.name.id

    @api.depends("print_count_ids.quantity")
    def _get_label_count(self):
        self.label_count = sum(line.quantity for line in self.print_count_ids)

    @api.model
    def default_get(self, fields_list):
        ret = super(PrintWizard, self).default_get(fields_list)
        return ret

    def get_print(self):
        if not self.name and self.model != 'stock.quant':
            raise UserError("Select label and try again.")
        if self.model == 'stock.quant':
            return self.sudo()._action_report_stock_quant_label()
        if self.model == 'product.template':
            return self.sudo()._action_report_product_label()
        elif self.model == "stock.lot":
            return self.sudo()._action_report_lot_label()
        elif self.model == "stock.picking":
            return self.sudo()._action_report_picking_label()
        elif self.model == 'stock.location':
            return self.sudo()._action_report_stock_location()
        return True

    def _action_report_product_label(self):
        return self.env.ref('bista_zpl_labels.report_product_template_label') \
            .report_action(docids=self.product_ids.ids,
                           data={'label': self.name.id, 'product_ids': self.product_ids.ids})

    def _action_report_stock_location(self):
        return self.env.ref('bista_zpl_labels.report_stock_location_label') \
            .report_action(docids=self.location_ids.ids,
                           data={'label': self.name.id, 'location_ids': self.location_ids.ids})

    def _action_report_lot_label(self):
        return self.env.ref('bista_zpl_labels.stock_production_lot_label') \
            .report_action(docids=self.lot_ids.ids,
                           data={'label': self.name.id, 'lot_ids': self.lot_ids.ids})

    def _action_report_picking_label(self):
        zpl_labels = self._get_multi_label(move=True)
        return self.env.ref("bista_zpl_labels.report_stock_picking_label") \
            .report_action(docids=self.picking_ids.ids,
                           data={'label': zpl_labels})

    def _action_report_stock_quant_label(self):
        zpl_labels = self._get_multi_label()
        print("Label data ", zpl_labels)
        return self.env.ref("bista_zpl_labels.report_stock_quant_label") \
            .report_action(docids=self.quant_ids.ids,
                           data={'label': zpl_labels})

    def _get_multi_label(self, move=False):
        move_ids = self.print_count_ids

        if not move_ids:
            raise UserError("nothing to print")

        if not self.lot_label and not self.product_label:
            raise UserError("you have not selected any label template.")

        lot_label = self.lot_label
        product_label = self.product_label

        zpl_labels = []
        for rec in move_ids:
            if not rec.quantity:
                continue

            product_record = rec.product_id
            lot_record = rec.lot_id

            if move:
                product_record = rec.move_line_id
                lot_record = rec.move_line_id

            if lot_record:
                if not lot_label:
                    raise UserError("Selected picking label does not have a valid lot template.")
                zpl = lot_label._get_label_date(lot_record)
            else:
                if not product_label:
                    raise UserError("Selected picking label does not have a valid product template.")
                zpl = product_label._get_label_date(product_record)
            zpl_labels.append(zpl * rec.quantity)
        return "".join(zpl_labels)


class LabelCount(models.TransientModel):
    _name = "print.wizard.print_count"
    _description = "Print.Wizard.Count"

    product_id = fields.Many2one('product.template')
    location_id = fields.Many2one('stock.location')
    lot_id = fields.Many2one('stock.lot')
    quantity = fields.Integer(default=1)
    print_wizard_id = fields.Many2one('print.wizard')
    model = fields.Selection(related="print_wizard_id.model")
    move_line_id = fields.Many2one('stock.move.line')
