# -*- encoding: utf-8 -*-
##############################################################################
#
# Bista Solutions Pvt. Ltd
# Copyright (C) 2024 (http://www.bistasolutions.com)
#
##############################################################################


from odoo import fields, models, api, _


class OrderAckDataQueue(models.Model):
    _name = "order.ack.data.queue"
    _description = 'Order Acknowledge Data Queue'
    _inherit = 'mail.thread'

    name = fields.Char(string="Reference", copy=False)
    edi_config_id = fields.Many2one(
        'edi.config', string='EDI Configuration', tracking=True)
    edi_order = fields.Char("EDI Order")
    so_order_id = fields.Many2one(
        'sale.order', string='Sale Order', readonly=True)
    edi_type = fields.Selection([('846', 'EDI-846'), ('850', 'EDI-850'), ('855', 'EDI-855'),
                                 ('860', 'EDI-860'), ('865', 'EDI-865'), ('856',
                                                                          'EDI-856'), ('810', 'EDI-810'),
                                 ('811', 'EDI-811')],
                                default='855', readonly=True)
    edi_order_data = fields.Text("Order Data", readonly=True)
    edi_error_log = fields.Text("Error Log", readonly=True)
    path = fields.Char(string="File Path", readonly=True)
    state = fields.Selection([
        ('draft', 'Draft'), ('submit', 'Submitted'), ('fail', 'Fail')],
        string='Status', help='Connection status of records',
        default='draft', tracking=True)
    # partner_id = fields.Many2one(related="edi_config_id.partner_id", string='Customer')

    @api.model_create_multi
    def create(self, vals_list):
        """
            This method creates sequence for each record.
            :return:
            @author: Gauri Shenoy @Bista Solutions Pvt. Ltd.
        """
        for vals in vals_list:
            if not vals.get('name'):
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'order.ack.data.queue') or _('New')
        return super(OrderAckDataQueue, self).create(vals_list)

    def export_data(self):
        """
            Button action to export the single Order ACK data queue to outbound file path.
            :return:
            @author: Gauri Shenoy @Bista Solutions Pvt. Ltd.
        """
        for rec in self:
            try:
                rec.edi_config_id.export_edi_data(rec.edi_order_data, rec.path)
            except Exception as e:
                self.update({'edi_error_log': str(e), 'state': 'fail'})
            else:
                self.update({'state': 'submit'})

    def reset_to_draft(self):
        """
            Button action to reset to draft.
            :return:
            @author: Gauri Shenoy @Bista Solutions Pvt. Ltd.
        """
        self.update({'state': 'draft', 'edi_error_log': ''})
