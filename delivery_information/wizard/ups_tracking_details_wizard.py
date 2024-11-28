from odoo import models, fields, api,_

"""
Wizard for Ups for get the tracking details
"""

class TrackingWizard(models.TransientModel):
    _name = 'ups.tracking.wizard'

    track_number = fields.Char('Track No')
    delivery_id = fields.Many2one('stock.picking',string="Delivery No")
    status = fields.Char('Status')
    Location = fields.Char('Location')
    start_from = fields.Char('From')
    dest_location = fields.Char('Destination Location')
    receivedByName = fields.Char('Received By')
    #
    start_from_date = fields.Char('Date')
    package_reached = fields.Char('We have your package ')
    label_date = fields.Char('Date')
    on_the_way3 = fields.Char('On the way')
    on_the_way_date = fields.Char('Date')
    out_for_delivery = fields.Char('Out For Delivery')
    out_for_delivery_date = fields.Char('Date')
    delivered = fields.Char('Delivered')
    delivered_date = fields.Char('Date')
    track_id = fields.Many2one('tracking.wizard')

    # file = fields.Binary('Track Details')
    # attachment_id = fields.Many2one('ir.attachment', string="Attachment")

    @api.model
    def default_get(self, default_fields):
        res = super(TrackingWizard, self).default_get(default_fields)
        data = self.env['ups.track.line'].browse(self._context.get('active_ids', []))

        track_id = self.env['tracking.details'].search([('track_no','=',data.track_no),('picking_id','=',data.picking_id.id)])

        update = []
        res.update({
            'track_number':data.track_no,
            'delivery_id':data.picking_id,
            'receivedByName':track_id.receivedByName,
            'start_from':track_id.location,
            'start_from_date':track_id.from_date,
            'Location':track_id.start_from,
            # 'package_reached':track_id.package_reached,
            'label_date':track_id.label_date,
            'on_the_way3':track_id.on_the_way3,
            'on_the_way_date':track_id.on_the_way_date,
            'out_for_delivery':track_id.out_for_delivery,
            'out_for_delivery_date':track_id.out_for_delivery_date,
            'delivered':track_id.delivered,
            'delivered_date':track_id.delivered_date,
            'status':track_id.status,
            'dest_location':track_id.dest_location,
            # 'attachment_id':track_id.attachment_id,
        })
        return res

# model that store the
class TrackingWizardLine(models.TransientModel):
    _name = 'tracking.route.wizard'




