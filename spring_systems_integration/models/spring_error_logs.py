# -*- coding: utf-8 -*-
##############################################################################
#
# Bista Solutions Pvt. Ltd
# Copyright (C) 2023 (https://www.bistasolutions.com)
#
##############################################################################

from odoo import models, fields


class SpringSystemsErrorLog(models.Model):
    _name = "spring.systems.error.log"
    _order = 'id desc'
    _description = "Spring Systems Error Log"

    name = fields.Char('Name')
    message = fields.Text('Message')
    request = fields.Text('Request')
    request_type = fields.Selection([
        ('get', 'GET'), ('post', 'POST'),
        ('put', 'PUT'), ('delete', 'DELETE'),
        ('patch', 'PATCH')], 'Request Type')
    response = fields.Text('Response')
    status = fields.Text('status')
    user_id = fields.Many2one('res.users', 'Request User')
    partner_id = fields.Many2one('res.partner', 'Partner')
    api_headers = fields.Text('Headers')
    api_url = fields.Char('URL')
    request_payload = fields.Text('Request payload')
    response_data = fields.Text('API Response')