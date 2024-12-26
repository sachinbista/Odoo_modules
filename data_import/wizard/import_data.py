# -*- encoding: utf-8 -*-
##############################################################################
#
#    Bista Solutions Pvt. Ltd
#    Copyright (C) 2012 (http://www.bistasolutions.com)
#
##############################################################################

from odoo import fields, models, exceptions, api, _, SUPERUSER_ID
from datetime import datetime
import xlrd
import tempfile
import base64
import re


class ProductDataImport(models.TransientModel):
    _name = 'product.data.import'
    _description = 'Import Product Data'

    object_name = fields.Selection([
        ('agent_commission', 'Agent Commission'),
    ], string='Object Name')
    file_to_import = fields.Binary('File To Import', required=True)
    file_name = fields.Char('File name', required=True)

    def action_import(self):
        """Load Master data from the Excel file."""
        if not self.file_to_import:
            raise exceptions.Warning(_("You need to select a file!"))
        binary_data = self.file_to_import
        file_name = self.file_name
        f = tempfile.NamedTemporaryFile(mode='wb+', delete=False)
        filename = '/tmp/' + str(file_name)
        with open(filename, 'wb') as f:
            x = base64.b64decode(binary_data)
            f.write(x)
        workbook = xlrd.open_workbook(filename)
        num_rows = workbook.sheet_by_index(0).nrows - 1
        curr_row = 0
        cr = self._cr
        l = ''
        while curr_row < num_rows:
            curr_row += 1
            if curr_row > 0:
                row = workbook.sheet_by_index(0).row(curr_row)
                if self.object_name == 'agent_commission':
                    commission_obj = self.env['agent.commission']

                    Commission_Partner = str(row[0].value)
                    Agent = str(row[1].value)
                    Commission_Code = str(row[2].value)

                    # Search or create Commission Partner
                    com_partner = self.env['res.partner'].search([('name', '=', Commission_Partner)], limit=1)
                    if not com_partner:
                        com_partner = self.env['res.partner'].create({'name': Commission_Partner})
                    com_partner_id = com_partner.id

                    # Search or create Agent
                    agent = self.env['res.partner'].search([('name', '=', Agent), ('agent', '=', True)], limit=1)
                    # if not agent:
                    #     agent = self.env['res.partner'].create({'name': Agent, 'agent': True})
                    agent_id = agent.id

                    # Search or create Commission Code
                    commission_code = self.env['commission'].search([('name', '=', Commission_Code)], limit=1)
                    if not commission_code:
                        commission_code = self.env['commission'].create({'name': Commission_Code})
                    commission_code_id = commission_code.id

                    if com_partner_id and agent_id and commission_code_id:
                        commission_id = commission_obj.search(
                            [('agent_id', '=', agent_id), ('agent_partner_id', '=', com_partner_id),
                             ('commission_id', '=', commission_code_id)], limit=1)
                        if not commission_id:
                            commission_vals = {
                                'agent_id': agent_id,
                                'agent_partner_id': com_partner_id,
                                'commission_id': commission_code_id
                            }
                            res = commission_obj.create(commission_vals)