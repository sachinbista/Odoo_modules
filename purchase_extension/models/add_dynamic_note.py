# -*- coding: utf-8 -*-

from odoo import api, fields, models, _

class AddDynamicNote(models.Model):
    _name = 'add.dynamic.note'

    name = fields.Char(string="Name", required=True)
    note = fields.Text(string="Description")



    