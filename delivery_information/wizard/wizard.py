from odoo import models, fields, api,_

"""
Wizard for Fedex for get the tracking details
"""

class TrackingWizard(models.TransientModel):
    _name = 'tracking.wizard'

    track_number = fields.Char('Track No')
    delivery_id = fields.Many2one('stock.picking',string="Delivery No")
    # track_line = fields.One2many('tracking.route.wizard','track_id')

    receivedByName = fields.Char('Received By')
    start_from = fields.Char('From')
    start_from_date = fields.Char('Date')
    package_reached = fields.Char('We have your package ')
    package_reached_date = fields.Char('Date')
    on_the_way3 = fields.Char('On the way')
    on_the_way_date = fields.Char('Date')
    out_for_delivery = fields.Char('Out For Delivery')
    out_for_delivery_date = fields.Char('Date')
    delivered = fields.Char('Delivered')
    delivered_date = fields.Char('Date')

    # track_id = fields.Many2one('tracking.wizard')
    status = fields.Char('Status')
    Location = fields.Char('Location')

    file = fields.Binary('Track Details')
    attachment_id = fields.Many2one('ir.attachment', string="Attachment")

    @api.model
    def default_get(self, default_fields):
        res = super(TrackingWizard, self).default_get(default_fields)
        data = self.env['fedex.track.line'].browse(self._context.get('active_ids', []))
        track_id = self.env['tracking.details'].search([('track_no','=',data.track_no),('picking_id','=',data.picking_id.id),('status','=',data.status)])
        update = []
        res.update({
            'track_number':data.track_no,
            'delivery_id':data.picking_id,
            'receivedByName':track_id.receivedByName,
            'start_from':track_id.start_from,
            'start_from_date':track_id.start_from_date,
            'package_reached':track_id.package_reached,
            'package_reached_date':track_id.package_reached_date,
            'on_the_way3':track_id.on_the_way3,
            'on_the_way_date':track_id.on_the_way_date,
            'out_for_delivery':track_id.out_for_delivery,
            'out_for_delivery_date':track_id.out_for_delivery_date,
            'delivered':track_id.delivered,
            'delivered_date':track_id.delivered_date,
            'status':track_id.status,
            'attachment_id':track_id.attachment_id,
        })
        return res

# model that store the
class TrackingWizardLine(models.TransientModel):
    _name = 'tracking.route.wizard'




