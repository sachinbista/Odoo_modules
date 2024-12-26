# -*- encoding: utf-8 -*-
##############################################################################
#
# Bista Solutions Pvt. Ltd
# Copyright (C) 2023 (http://www.bistasolutions.com)
#
##############################################################################

from odoo import fields, models
from odoo.exceptions import UserError
import base64
import csv
import paramiko


class CustomInventoryEmailLog(models.Model):
    _name = "custom.inventory.emaillog"
    _description = "Inventory Email Log"

    name = fields.Char("Name")


class StockQuant(models.Model):
    _inherit = 'stock.quant'

    def run_inventory_report(self):
        """
        Checking all the active SFTP connections in the success state.
        """
        ftp_connection_record = self.env['bista.sftp.connection'].search([('state', '=', 'success')])
        for rec in ftp_connection_record:
            hostname = rec.hostname
            port_no = rec.port_no
            sftp_username = rec.sftp_username
            sftp_passwd = rec.sftp_passwd
            sftp_file_path = rec.sftp_file_path
            company = rec.company_id
            """
            Using this function cron will run and generate .csv file.
            """
            product_ids = [p for p in self.env['product.product'].search(
                [('type', '=', 'product'), ('is_export_stock', '=', True)])]

            product_data_list = []
            for product in product_ids:
                stock_quant = self.env['stock.quant'].search([
                    ('company_id', '=', company.id),
                    ('product_id', 'in', product.ids),
                    ('on_hand', '=', True)]).mapped('available_quantity')
                export_available_quantity = self.env['product.export.stock.line'].search([
                    ('product_export_id', 'in', product.product_tmpl_id.ids)]).mapped('available_quantity')
                free_total_qty = sum(stock_quant) + sum(export_available_quantity)
                if rec.customer_id:
                    product_part_no = self.env['product.alias.part.number'].search(
                        [('customer_id', '=', rec.customer_id.id),
                         ('product_id', 'in', product.ids)]).mapped('part_no')
                    if product_part_no:
                        product_data = {
                            'name': product.name,
                            'default_code': product.default_code,
                            'company': product.company_id.id,
                            'free_qty': free_total_qty if free_total_qty else 0,
                            'part_no': product_part_no[0] if product_part_no else 0,
                        }
                        product_data_list.append(product_data)
                else:
                    product_data = {
                        'name': product.name,
                        'default_code': product.default_code,
                        'company': product.company_id.id,
                        'free_qty': free_total_qty if free_total_qty else 0,
                    }
                    product_data_list.append(product_data)

            filename = 'inv_export' + '.csv'

            with open(filename, 'w', newline='') as csvfile:
                csvwriter = csv.writer(csvfile)

                if rec.customer_alias and not rec.product_internal_ref:
                    header = ['sku', 'quantity_available']
                elif rec.product_internal_ref and not rec.customer_alias:
                    header = ['SKU', 'QTY', 'Internal Ref']
                elif rec.product_internal_ref and rec.customer_alias:
                    header = ['SKU', 'quantity_available', 'Internal Ref']
                else:
                    header = ['SKU', 'QTY']
                csvwriter.writerow(header)

                for data in product_data_list:
                    if data.get('part_no'):
                        product_name = data.get('part_no')
                    elif data.get('default_code'):
                        product_name = data.get('default_code')
                    elif data.get('name'):
                        product_name = data.get('name')

                    if rec.product_internal_ref or rec.product_internal_ref and rec.customer_alias:
                        internal_ref = data.get('default_code') or ''
                        row = [product_name, int(data.get('free_qty')), internal_ref]
                    else:
                        row = [product_name, int(data.get('free_qty'))]
                    csvwriter.writerow(row)

            report_csv = filename

            # After generating the CSV file, establish an SFTP connection and upload the file
            try:
                sftp, ssh = self.establish_sftp_connection(
                    hostname, port_no, sftp_username, sftp_passwd, sftp_file_path)

                remote_directory = sftp_file_path

                # Upload the CSV file to the SFTP server
                sftp.put(report_csv, remote_directory)

                print(f"CSV file '{filename}' uploaded successfully to SFTP server.")
            except Exception as e:
                print(f"Error uploading CSV file to SFTP server: {str(e)}")
            finally:
                # Close the SFTP session and SSH connection
                sftp.close()

    def establish_sftp_connection(self, hostname, port_no, sftp_username, sftp_passwd, sftp_file_path):
        try:
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

            # Connect to the SFTP server using SSH credentials
            ssh.connect(
                hostname=hostname,
                port=port_no,
                username=sftp_username,
                password=sftp_passwd,
            )
            # Open an SFTP session
            sftp = ssh.open_sftp()
            # Return the SFTP and SSH transport objects
            return sftp, ssh
        except Exception as e:
            print(f"Error connecting to SFTP server: {str(e)}")
            return None, None
