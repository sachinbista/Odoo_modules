# -*- encoding: utf-8 -*-
##############################################################################
#
#    Bista Solutions Pvt. Ltd
#    Copyright (C) 2023 (http://www.bistasolutions.com)
#
##############################################################################


from odoo import api, fields, models
from odoo.exceptions import UserError


class StockPicking(models.Model):
    _inherit = 'stock.picking'


    def generate_sscc_barcode(self, package=False):
        """
            This method is used to generate the SSCC-18 barcode of 17 digits.
            :return:
        """
        barcode_list = []
        cnt = 1
        barcode_number=0
        if not package:
            package = self.package_ids
        for rec in package:
            split_pack_no = rec.name[4:]
            gs1_extension_digit = self.env['ir.config_parameter'].sudo().get_param(
                'bista_GS1_shipping_label.gs1_extension_digit')
            gs1_company_prefix = self.env['ir.config_parameter'].sudo().get_param(
                'bista_GS1_shipping_label.gs1_company_prefix')

            barcode_number = gs1_extension_digit + gs1_company_prefix + split_pack_no
            barcode_list.append(barcode_number)
            print("cntttt", cnt)
            barcode_number = barcode_list[0] if len(barcode_list) > 0 else None
            cnt += 1
            print("cntttt",cnt)
            print("barcccccc",barcode_number)
            print("barcccccc",barcode_list)
            print(">>>>>barcoedeeeee", barcode_number)
        return barcode_number
        # barcode = barcode_list[0]
        # else:
        #     barcode = None
        # return barcode_number

    def get_check_digit(self, package):
        """
            This method is used to generate the check digit of the SSCC-18 Barcode.
            :return:
        """
        barcode_values = self.generate_sscc_barcode(package)

        for value in barcode_values:
            number_length = len(value)
            if number_length < 7 or number_length > 17:
                raise UserError("Invalid length for SSCC-18 Barcode")
            mul_digit = 3
            check_digit_sum = 0
            temp_check_digit = ''
            for digit in value[::-1]:
                check_digit_sum += int(digit) * mul_digit
                mul_digit = 1 if mul_digit == 3 else 3
            if check_digit_sum % 10 == 0:
                check_digit = 0
            else:
                temp_check_digit = int(check_digit_sum)
                while temp_check_digit % 10 != 0:
                    temp_check_digit += 1
                check_digit = int(temp_check_digit) - check_digit_sum
            # application_identifier = '(' + self.company_id.gs1_application_id + ')'
            # full_barcode = application_identifier + ' ' + value + str(check_digit)
            full_barcode = value + str(check_digit)
            return full_barcode
