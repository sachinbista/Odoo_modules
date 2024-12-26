# -*- encoding: utf-8 -*-
##############################################################################
#
# Bista Solutions Pvt. Ltd
# Copyright (C) 2023 (http://www.bistasolutions.com)
#
##############################################################################
import base64
import logging

import xlrd

from odoo import _, fields, models
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class ImportProductData(models.TransientModel):
    _name = 'import.product.data'
    _description = 'Import Product Data'

    data_file = fields.Binary('File', required=True)
    file_name = fields.Char("File Name")

    def get_attributes_data(self, attribute_name):
        """ Check attribute name."""
        if attribute_name:
            attribute_id = self.env['product.attribute'].search([
                ('name', '=', attribute_name),
            ])
            if not attribute_id:
                product_attribute_id = self.env['product.attribute'].create(
                    {'name': attribute_name})
                return product_attribute_id
            return attribute_id

    def get_attributes_values_data(self, row, attribute_val, product_attribute_id):
        """ Check attribute values."""
        if not product_attribute_id and attribute_val:
            raise UserError(
                _("Set Attribute name for '%s' (row: %d).") % (attribute_val, row))
        if product_attribute_id and not attribute_val:
            raise UserError(
                _("Set Attribute value for '%s' (row: %d).") % (product_attribute_id.name, row))
        if product_attribute_id and attribute_val:
            attribute_val_id = self.env['product.attribute.value'].search([
                ('name', '=', attribute_val),
                ('attribute_id', '=', product_attribute_id.id),
            ])
            if not attribute_val_id:
                product_attribute_val_id = self.env['product.attribute.value'].create({
                    'name': attribute_val,
                    'attribute_id': product_attribute_id.id,
                })
                return product_attribute_val_id
            return attribute_val_id

    def get_product_type(self, product_type):
        """ Check UOM."""
        type_dict = {
            'Consumable': 'consu',
            'Service': 'service',
            'Gift Card': 'gift',
            'Storable Product': 'product',
            'Event Ticket': 'event',
            'Event Booth': 'event_booth',
        }
        if product_type:
            return type_dict[product_type]
        else:
            return type_dict['Consumable']

    # def get_invoice_policy(self, option):
    #     """ Check UOM."""
    #     option_dict = {
    #         'Ordered quantities': 'order',
    #         'Delivered quantities': 'delivery'
    #     }
    #     if option:
    #         return option_dict[option]

    def get_product_category(self, category, parent_category):
        """ Check category."""
        product_category_obj = self.env['product.category']
        if category:
            parent_category_id = product_category_obj.search([('name', '=', parent_category)], limit=1) 
            if not parent_category_id:
                parent_category_id = product_category_obj.create({'name': parent_category})
            category_id = product_category_obj.search([
                ('name', '=', category),
                ('parent_id', '=', parent_category_id.id)
            ], limit=1)
            if not category_id:
                category_id = product_category_obj.create({'name': category, 'parent_id': parent_category_id.id})
            return category_id.id

    def import_product_template(self):
        ''' Import Product data from uploaded file.'''
        if not self.file_name.split('.')[-1] in ['xlsx', 'xls']:
            raise UserError(_("Please upload the file in Excel format."))
        binary_data = self.data_file
        decode_binary_data = base64.decodebytes(binary_data)
        book = xlrd.open_workbook(file_contents=decode_binary_data)
        worksheet = book.sheet_by_index(0)
        worksheet_rows = worksheet.nrows
        # Check file content
        if worksheet_rows <= 1:
            raise UserError(_("Uploaded file is empty."))

        product_tmpl_obj = self.env['product.template']
        total_data_row = worksheet_rows - 1
        # start_row = 1
        cols_list = worksheet.row_values(0, 0, None) + ['row']
        data = []

        for row in range(1, worksheet_rows):
            data_dict = dict(zip(cols_list, worksheet.row_values(row, 0, None)))  # {'col1': value1, 'col2': value2}
            data_dict['row'] = row
            data.append(data_dict)
        try:
            # while start_row <= total_data_row:
            for line in data:
                vals = {}
                # row = worksheet.row(start_row)
                row_line = line['row']
                # -------------- internal reference/SKU --------------
                # internal_ref = row[0].value.strip()
                internal_ref = line.get('Product Code') and str(line['Product Code']).strip()
                # part_no = line.get('RM PN') and line.get('RM PN').strip()

                barcode = line.get('Barcode') and str(line['Barcode']).strip()
                # ean = line.get('EAN') and line.get('EAN').strip()
                # gtin = line.get('GTIN-14') and line.get('GTIN-14').strip()
                invoice_policy = line.get('Invoicing Policy') and line.get('Invoicing Policy').strip()
                standard_price = line.get('Cost') and str(line.get('Cost')).strip()
                lst_price = line.get('Wholesale') and str(line.get('Wholesale')).strip()

                # -------------- category_id --------------
                categ_name = line.get('Subcategory') and line.get('Subcategory').strip()
                parent_categ_name = line.get('Category') and line.get('Category').strip()
                categ_id = self.get_product_category(categ_name, parent_categ_name)
                # categ_id = product_category_obj.search([
                #     ('name', '=', categ_id),
                # ])
                # if categ_id:
                #     categ_id = categ_id.id
                # if not categ_id:
                #     product_category_obj.create({'name': categ_id})

                # -------------- product name --------------
                product_name = line.get('Name') and line['Name'].strip()
                main_product = line.get('Main Product') and line['Main Product'].strip()

                # -------------- Attribute name --------------
                attribute_list = []
                attribute_val_list = []
                attribute_name = line.get('Option Name') and str(line['Option Name']).strip()
                product_attribute_id = self.get_attributes_data(
                    attribute_name=attribute_name)
                if product_attribute_id and product_attribute_id.id not in attribute_list:
                    attribute_list.append(product_attribute_id.id)

                # -------------- Attribute value --------------
                attribute_val = line.get('Option value') and str(line['Option value']).strip()
                if attribute_val:
                    product_attribute_val_id = self.get_attributes_values_data(
                    row=row_line, attribute_val=attribute_val, product_attribute_id=product_attribute_id)
                    if product_attribute_val_id and product_attribute_val_id.id not in attribute_val_list:
                        attribute_val_list.append(product_attribute_val_id.id)

                ## -------------- Attribute name1 --------------
                attribute_name1 = line.get('Option Name1') and str(line['Option Name1']).strip()
                product_attribute_id1 = self.get_attributes_data(
                    attribute_name=attribute_name1)
                if product_attribute_id1 and product_attribute_id1.id not in attribute_list:
                    attribute_list.append(product_attribute_id1.id)
                ## -------------- Attribute value1 --------------
                attribute_val1 = line.get('Option value1') and str(line['Option value1']).strip()
                if attribute_val1:
                    product_attribute_val_id1 = self.get_attributes_values_data(
                        row=row_line, attribute_val=attribute_val1, product_attribute_id=product_attribute_id1)
                    if product_attribute_val_id1 and product_attribute_val_id1.id not in attribute_val_list:
                        attribute_val_list.append(product_attribute_val_id1.id)

                ## -------------- Attribute name2 --------------
                attribute_name2 = line.get('Option Name2') and str(line['Option Name2']).strip()
                product_attribute_id2 = self.get_attributes_data(
                    attribute_name=attribute_name2)
                if product_attribute_id2:
                    product_attribute_id2 = product_attribute_id2[0]
                if product_attribute_id2 and product_attribute_id2.id not in attribute_list:
                    attribute_list.append(product_attribute_id2.id)
                ## -------------- Attribute value2 --------------
                attribute_val2 = line.get('Option value2') and str(line['Option value2']).strip()
                if attribute_val2:
                    product_attribute_val_id2 = self.get_attributes_values_data(
                        row=row_line, attribute_val=attribute_val2, product_attribute_id=product_attribute_id2)
                    if product_attribute_val_id2 and product_attribute_val_id2.id not in attribute_val_list:
                        attribute_val_list.append(product_attribute_val_id2.id)

                ## -------------- Attribute name3 --------------
                attribute_name3 = line.get('Option Name3') and str(line['Option Name3']).strip()
                product_attribute_id3 = self.get_attributes_data(
                    attribute_name=attribute_name3)
                if product_attribute_id3 and product_attribute_id3.id not in attribute_list:
                    attribute_list.append(product_attribute_id3.id)
                ## -------------- Attribute value3 --------------
                attribute_val3 = line.get('Option value3') and str(line['Option value3']).strip()
                if attribute_val3:
                    product_attribute_val_id3 = self.get_attributes_values_data(
                        row=row_line, attribute_val=attribute_val3, product_attribute_id=product_attribute_id3)
                    if product_attribute_val_id3 and product_attribute_val_id3.id not in attribute_val_list:
                        attribute_val_list.append(product_attribute_val_id3.id)

                ## -------------- Attribute name4 --------------
                attribute_name4 = line.get('Option Name4') and str(line['Option Name4']).strip()
                product_attribute_id4 = self.get_attributes_data(
                    attribute_name=attribute_name4)
                if product_attribute_id4 and product_attribute_id4.id not in attribute_list:
                    attribute_list.append(product_attribute_id4.id)
                ## -------------- Attribute value4 --------------
                attribute_val4 = line.get('Option value4') and str(line['Option value4']).strip()
                if attribute_val4:
                    product_attribute_val_id4 = self.get_attributes_values_data(
                        row=row_line, attribute_val=attribute_val4, product_attribute_id=product_attribute_id4)
                    if product_attribute_val_id4 and product_attribute_val_id4.id not in attribute_val_list:
                        attribute_val_list.append(product_attribute_val_id4.id)

                # -------------- Sales Description --------------
                # sales_description = line.get('Sales Description') and str(line['Sales Description']).strip()
                # vals['variant_description_sale'] = sales_description

                # Check Product
                product_tmpl_id = product_tmpl_obj.search([
                    ('name', '=', main_product),
                ])
                attribute_ids = self.env['product.attribute'].browse(
                    attribute_list)
                if not product_tmpl_id:
                    # -------------- Product type --------------
                    product_type = line.get('Product type') and line['Product type'].strip()
                    vals['detailed_type'] = self.get_product_type(
                        product_type=product_type)
                    # vals['invoice_policy'] = self.get_invoice_policy(
                    #     option=invoice_policy)
                    varient_list = []
                    for attribute in attribute_ids:
                        attribute_val_id = self.env['product.attribute.value'].search([
                            ('id', 'in', attribute_val_list),
                            ('attribute_id', '=', attribute.id),
                        ])
                        varient_list.append((0, 0, {
                            'attribute_id': attribute.id,
                            'value_ids': [(6, 0, attribute_val_id.ids)],
                        }))
                    vals['attribute_line_ids'] = varient_list
                    vals['name'] = main_product
                    vals['default_code'] = internal_ref
                    vals['barcode'] = barcode
                    # vals['ean'] = ean
                    # vals['gtin'] = gtin
                    vals['invoice_policy'] = invoice_policy
                    vals['standard_price'] = float(standard_price)
                    vals['list_price'] = float(lst_price)
                    vals['categ_id'] = categ_id
                    product_tmpl_id = product_tmpl_obj.create(vals)
                    product_id = self.env['product.product'].search([
                        ('product_tmpl_id', '=', product_tmpl_id.id),
                    ])
                    if product_id:
                        product_id.write({
                            'default_code': internal_ref,
                            'barcode': barcode,
                            # 'ean': ean,
                            # 'gtin': gtin,
                            'invoice_policy': invoice_policy,
                            'standard_price': float(standard_price),
                            'list_price': float(lst_price)
                            # 'variant_description_sale': sales_description
                        })
                else:
                    vals['standard_price'] = float(standard_price)
                    vals['list_price'] = float(lst_price)
                    product_tmpl_id.write(vals)
                    product_tmpl_attribute_val_ids = []
                    for attribute in attribute_ids:
                        attribute_val_id = self.env['product.attribute.value'].search([
                            ('id', 'in', attribute_val_list),
                            ('attribute_id', '=', attribute.id),
                        ])
                        attribute_line_id = product_tmpl_id.attribute_line_ids.filtered(
                            lambda line: line.attribute_id.id == attribute.id)

                        if not attribute_line_id:
                            product_tmpl_id.write({
                                'attribute_line_ids': [(0, 0, {
                                    'attribute_id': attribute.id,
                                    'value_ids': [(6, 0, attribute_val_id.ids)],
                                })]
                            })
                            attribute_line_id = product_tmpl_id.attribute_line_ids.filtered(
                                lambda line: line.attribute_id.id == attribute.id)
                        a = []
                        ## Updating the attribute value if attribute is already available.
                        attribute_value_list = attribute_line_id.value_ids.ids
                        attribute_value_list += attribute_val_id.ids
                        attribute_line_id.write({
                            'value_ids': [(6, 0, list(set(attribute_value_list)))]
                        })
                        if line.get('Option Name'):
                            attribute_id1 = self.env['product.attribute'].search(
                                [('name', '=', line.get('Option Name'))]).id
                            prod_att_value1 = self.env['product.attribute.value'].search(
                                [('attribute_id', '=', attribute_id1),
                                 ('name', '=', line.get('Option value').strip())]).id
                            prod_tmpl_att_val_id1 = self.env['product.template.attribute.value'].search(
                                [('attribute_id', '=', attribute_id1),
                                 ('product_attribute_value_id', '=', prod_att_value1),
                                 ('product_tmpl_id', '=', product_tmpl_id.id)]).id
                            if prod_tmpl_att_val_id1:
                                a.append(prod_tmpl_att_val_id1)
                        if line.get('Option Name1'):
                            attribute_id2 = self.env['product.attribute'].search(
                                [('name', '=', line.get('Option Name1'))]).id

                            prod_att_value2 = self.env['product.attribute.value'].search(
                                [('attribute_id', '=', attribute_id2),
                                 ('name', '=', str(line.get('Option value1')).strip())]).id

                            prod_tmpl_att_val_id2 = self.env['product.template.attribute.value'].search(
                                [('attribute_id', '=', attribute_id2),
                                 ('product_attribute_value_id', '=', prod_att_value2),
                                 ('product_tmpl_id', '=', product_tmpl_id.id)]).id

                            if prod_tmpl_att_val_id2:
                                a.append(prod_tmpl_att_val_id2)
                        if line.get('Option Name2'):
                            attribute_id3 = self.env['product.attribute'].search(
                                [('name', '=', line.get('Option Name2'))])[0].id


                            prod_att_value3 = self.env['product.attribute.value'].search(
                                [('attribute_id', '=', attribute_id3),
                                 ('name', '=', line.get('Option value2').strip())]).id

                            prod_tmpl_att_val_id3 = self.env['product.template.attribute.value'].search(
                                [('attribute_id', '=', attribute_id3),
                                 ('product_attribute_value_id', '=', prod_att_value3),
                                 ('product_tmpl_id', '=', product_tmpl_id.id)]).id

                            if prod_tmpl_att_val_id3:
                                a.append(prod_tmpl_att_val_id3)

                        if line.get('Option Name3'):
                            attribute_id4 = self.env['product.attribute'].search(
                                [('name', '=', line.get('Option Name3'))]).id
                            # attribute_val3 = line.get('Option value3') and str(line['Option value3']).strip()
                            prod_att_value4 = self.env['product.attribute.value'].search(
                                [('attribute_id', '=', attribute_id4),
                                 ('name', '=', line.get('Option value3') and str(line['Option value3']).strip())]).id

                            prod_tmpl_att_val_id4 = self.env['product.template.attribute.value'].search(
                                [('attribute_id', '=', attribute_id4),
                                 ('product_attribute_value_id', '=', prod_att_value4),
                                 ('product_tmpl_id', '=', product_tmpl_id.id)]).id

                            if prod_tmpl_att_val_id4:
                                a.append(prod_tmpl_att_val_id4)

                        if line.get('Option Name4'):
                            attribute_id5 = self.env['product.attribute'].search(
                                [('name', '=', line.get('Option Name4'))]).id

                            prod_att_value5 = self.env['product.attribute.value'].search(
                                [('attribute_id', '=', attribute_id5),
                                 ('name', '=', line.get('Option value4').strip())]).id

                            prod_tmpl_att_val_id5 = self.env['product.template.attribute.value'].search(
                                [('attribute_id', '=', attribute_id5),
                                 ('product_attribute_value_id', '=', prod_att_value5),
                                 ('product_tmpl_id', '=', product_tmpl_id.id)]).id

                            if prod_tmpl_att_val_id5:
                                a.append(prod_tmpl_att_val_id5)

                        a.sort()
                        b = str(a)
                        c = b.replace('[', '').replace(']', '').replace(' ', '')
                        product_id = self.env['product.product'].search([('combination_indices', '=', c)])
                        if product_id:
                            product_id.write({'default_code': internal_ref,
                                              # 'variant_description_sale': sales_description,
                                              'barcode': barcode,
                                              # 'ean': ean,
                                              # 'gtin': gtin,
                                              # 'invoice_policy': self.get_invoice_policy(option=invoice_policy),
                                              'standard_price': float(standard_price),
                                              'list_price': float(lst_price)
                                              })
        except Exception:
            raise
            _logger.warning("Failed to Import file.")
