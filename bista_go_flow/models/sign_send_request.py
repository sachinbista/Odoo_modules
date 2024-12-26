from odoo import api, fields, models, Command


class SignSendRequest(models.TransientModel):
    _inherit = 'sign.send.request'

    def create_request(self):
        if 'default_role_id' in self._context:
            template_id = self.template_id.id
            if self.signers_count:
                signers = [{'partner_id': signer.partner_id.id, 'role_id': signer.role_id.id,
                            'mail_sent_order': signer.mail_sent_order} for signer in self.signer_ids]
            else:
                signers = [{'partner_id': self.signer_id.id, 'role_id': self.env.ref('sign.sign_item_role_default').id,
                            'mail_sent_order': self.signer_ids.mail_sent_order}]
            cc_partner_ids = self.cc_partner_ids.ids
            reference = self.filename
            subject = self.subject
            message = self.message
            message_cc = self.message_cc
            attachment_ids = self.attachment_ids
            refusal_allowed = self.refusal_allowed
            sign_request = self.env['sign.request'].create({
                'template_id': template_id,
                'request_item_ids': [Command.create({
                    'partner_id': signer['partner_id'],
                    'role_id':  self._context.get('default_role_id') if 'default_role_id' in self._context else 1,
                    'mail_sent_order': signer['mail_sent_order'],
                }) for signer in signers],
                'reference': reference,
                'subject': subject,
                'message': message,
                'message_cc': message_cc,
                'attachment_ids': [Command.set(attachment_ids.ids)],
                'refusal_allowed': refusal_allowed,
                'picking_id': self._context.get('picking_id') if 'picking_id' in self._context else False,
            })
            sign_request.message_subscribe(partner_ids=cc_partner_ids)
            return sign_request
        return super(SignSendRequest, self).create_request()


class SignRequest(models.Model):
    _inherit = 'sign.request'

    picking_id = fields.Many2one('stock.picking', string='Transfer')