from odoo import models, fields, api, _
from odoo.exceptions import UserError

no_label_message = "Nothing to Print. If you believe this is due to a system error, please contact the system administrator"
no_copies_message = "Number of copies should be equal or greater than zero."


class PrintWizard(models.TransientModel):
    _inherit = "print.wizard"

    printer_id = fields.Many2one("printing.printer")
    custom_label = fields.Boolean()
    custom_label_data = fields.Text()


    def _action_print_custom(self):
        self.print_label({"value": self.custom_label_data})


    def _action_report_product_label(self):
        label = self.env["report.bista_zpl_labels.product_template_label_template"] \
            ._get_report_values(docids=self.product_ids.ids,
                                data={'label': self.name.id, 'product_ids': self.product_ids.ids})
        self.print_label(label)

    def _action_report_lot_label(self):
        label = self.env["report.bista_zpl_labels.stock_lot_label"] \
            ._get_report_values(docids=self.lot_ids.ids,
                                data={'label': self.name.id, 'lot_ids': self.lot_ids.ids})
        self.print_label(label)

    def _action_report_stock_location(self):
        label = self.env["report.bista_zpl_labels.stock_location_label_template"]._get_report_values(
            docids=self.location_ids.ids,
            data={'label': self.name.id, 'location_ids': self.location_ids.ids})
        self.print_label(label)

    def _action_report_picking_label(self):
        zpl_label = self._get_multi_label(move=True)
        self.print_label({"value": zpl_label})

    def _action_report_stock_quant_label(self):
        zpl_label = self._get_multi_label()
        self.print_label({"value": zpl_label})

    def print_label(self, label):
        value = label.get('value', False)

        if not value:
            raise UserError(no_label_message)

        if not self.copies:
            raise UserError(no_copies_message)

        if not self.printer_id:
            raise UserError("Select a printer nad try again.")
        value = value * self.copies
        # raise UserError(value)
        self.printer_id.print_document(
            self, value.encode(), doc_format="qweb - text", behavior={'action': 'server', 'tray': False}
        )
