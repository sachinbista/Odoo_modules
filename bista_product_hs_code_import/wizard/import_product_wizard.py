import tempfile
import binascii
import base64
import certifi
import urllib3
import xlrd
from odoo.exceptions import UserError
from odoo import fields, models, _


class ProductImport(models.TransientModel):
    """ Import Product data """
    _name = 'import.product.hs.code'
    _description = 'Product Import'

    file = fields.Binary(string="Upload File", help="Choose the file to upload")
    file_name = fields.Char(string="File Name", help="Name of the file")
    # option = fields.Selection([
    #     ('csv', 'CSV'),
    #     ('xlsx', 'XLSX')], default='csv', help="Choose the file type")

    def import_file(self):
        """ Function to import product details from csv or xlsx file """
        try:
            product_temp_obj = self.env['product.template'].sudo()
            product_obj = self.env['product.template'].sudo()
            file_string = tempfile.NamedTemporaryFile(suffix=".xlsx")
            file_string.write(binascii.a2b_base64(self.file))
            book = xlrd.open_workbook(file_string.name)
            sheet = book.sheet_by_index(0)
        except:
            raise UserError(_("Please choose the correct file"))
        startline = True
        company_id = self._context.get("allowed_company_ids")
        if company_id:
            company_id = self.env['res.company'].browse(company_id)
        for i in range(sheet.nrows):
            if startline:
                startline = False
            else:
                line = list(sheet.row_values(i))
                product_temp = product_temp_obj
                if line[1]:
                    product_temp = product_temp_obj.search(
                        [('barcode', '=', int(line[1]))], limit=1)
                elif line[2]:
                    product_temp = product_temp_obj.search(
                        [('default_code', '=', line[2])], limit=1)
                if product_temp:
                    if company_id.country_id.code == 'US':
                        product_temp.write({
                            'hs_code': line[12].strip(),
                        })
                    elif company_id.country_id.code == 'CA':
                        product_temp.write({
                            'hs_code': line[13].strip(),
                        })

                    elif company_id.country_id.code == 'GB':
                        product_temp.write({
                            'hs_code': line[14].strip(),
                        })
                    elif company_id.country_id.code == 'NL':
                        product_temp.write({
                            'hs_code': line[15].strip(),
                        })
                    elif company_id.country_id.code == 'AU':
                        product_temp.write({
                            'hs_code': line[16].strip(),
                        })
                else:
                    raise UserError(_(
                        "Product not available with UPC %s" % int(line[1])))
