# -*- encoding: utf-8 -*-
##############################################################################
#
#    Bista Solutions Pvt. Ltd
#    Copyright (C) 2023 (http://www.bistasolutions.com)
#
#############################################################################
from odoo import api, fields, models
from odoo import tools

STATE = [
    ('outgoing', 'Outgoing'),
    ('sent', 'Sent'),
    ('received', 'Received'),
    ('exception', 'Delivery Failed'),
    ('pending', 'Not Held'),
    ('cancel', 'Cancelled'),
    ('open', 'To Do'),
    ('done', 'Held'),
]


class CustomerOutReach(models.Model):
    _name = "customer.out.reach"
    _auto = False
    _description = "Customer Out Reach"

    _rec_name = 'partner'

    subject = fields.Char(string='Subject', readonly=True)
    desc = fields.Text(string='Description', readonly=True)
    state = fields.Selection(selection=STATE, string='State', readonly=True)
    date = fields.Datetime(string='Action Date', readonly=True)
    action = fields.Char(string='Action Type', readonly=True)
    partner = fields.Many2one(comodel_name='res.partner', string='Customer Name', readonly=True)

    def init(self):
        tools.drop_view_if_exists(self._cr, 'customer_out_reach')
        self._cr.execute(
            """ CREATE OR REPLACE VIEW customer_out_reach AS (

                SELECT message.id as "id", message.subject as "subject" , mail.body_html as "desc" ,mail.state as "state" , mail.create_date as "date" , 'E-Mail' as action , mail_partner.res_partner_id as "partner"

                from mail_mail as mail
                INNER JOIN mail_mail_res_partner_rel as mail_partner on (mail_partner.mail_mail_id = mail.id)
                INNER JOIN mail_message as message on (message.id = mail.mail_message_id)

                UNION

                SELECT phonecall.id as "id", phonecall.name as "subject", phonecall.phone as "desc",phonecall.state as "state", phonecall.create_date as "date",'Phone Call' as action , phonecall.partner_id as "partner"

                FROM voip_phonecall as phonecall


                ORDER BY "date" DESC 


            )"""
        )
