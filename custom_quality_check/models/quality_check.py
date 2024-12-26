from odoo import tools
from odoo import api, fields, models, _
import base64
from PIL import Image
from io import BytesIO
import requests
import json
import logging
from odoo.exceptions import ValidationError


class QualityCheck(models.Model):
    _inherit = "quality.check"
    _description = "Quality Check"

    compare_dimension_to = fields.Selection(
        [('	packaging', 'Packaging Dimension'), ('product', 'Product Dimension')], string="Compare To")
    packaging_name = fields.Char("Packaging")

    length = fields.Float("length")
    pkg_length = fields.Float("Package length")
    width = fields.Float("Width")
    pkg_width = fields.Float("Package Width")
    height = fields.Float("Height")
    pkg_height = fields.Float("Package Height")
    weight = fields.Float("Weight")
    pkg_weight = fields.Float("Package length")

    qty_line = fields.Float("Quantity")
    qty_to_test = fields.Float("Quantity to Test")
    qty_tested = fields.Float("Quantity Tested")



    picking_id = fields.Many2one('stock.picking', string="Picking")
    production_id = fields.Many2one('mrp.production', string="Production Order")
    partner_id = fields.Many2one('res.partner', string="Partner")

    scanned_image = fields.Binary("Scanned Image")
    dimensioner_type = fields.Selection(
        related='point_id.dimensioner_type', string='Dimensioner Type')
    dimension_status = fields.Boolean("Dimension Status", default=False)

    def action_get_dimensions(self):
        api_url = 'https://proxy.spectre-licensing.com/api/FlyBar%20SC%20Parcel%2001/dimension'
        api_image_path_url = 'https://proxy.spectre-licensing.com/api/FlyBar%20SC%20Parcel%2001/snapshot'
        api_image_url = 'https://proxy.spectre-licensing.com/api/FlyBar%20SC%20Parcel%2001/file'
        token = 'b2Rvby1pbnRlZ3JhdGlvbkBmbHliYXIuY29tOjBkT28tZkx5QjRSIQ=='
        # spectre_url = self.env['ir.config_parameter'].sudo().get_param('custom_quality_check.spectre_url')
        # token = self.env['ir.config_parameter'].sudo().get_param('custom_quality_check.spectre_token')
        # api_image_path_url = self.env['ir.config_parameter'].sudo().get_param('custom_quality_check.image_path_url')
        # api_image_url = self.env['ir.config_parameter'].sudo().get_param('custom_quality_check.image_url')
        #
        try:
            response = requests.get(api_url, headers={
                'Content-Type': 'application/json',
                'Accept': 'application/json',
                'Authorization': f'Bearer {token}'
            })
            response.raise_for_status()
            data = response.json()
            if response.status_code == 200 and data:
                dimension_info = data.get('Responses', {}).get('Dimension', {}).get('Info', {})
                length = dimension_info.get('Dimensions', {}).get('Length', 0)
                width = dimension_info.get('Dimensions', {}).get('Width', 0)
                height = dimension_info.get('Dimensions', {}).get('Height', 0)
                weight_info = dimension_info.get('Dimensions', {}).get('Weight', {})
                gross_weight = weight_info.get('Gross', 0)
                net_weight = weight_info.get('Net', 0)
                tare_weight = weight_info.get('Tare', 0)

                # self.update({
                #     'length': length if length and not self.length else False,
                #     'width': width if width and not self.width else False,
                #     'height': height if height and not self.height else False,
                #     'weight': gross_weight if gross_weight and not self.weight else False
                # })
                self.update({
                    'length': length if length  else False,
                    'width': width if width  else False,
                    'height': height if height else False,
                    'weight': gross_weight if gross_weight  else False,
                    'dimension_status': True
                })
                images_path = self.get_images_path(api_image_path_url, token)

                if images_path:
                    images_path = images_path.get('Responses', {}).get('Snapshot', {}).get('Directory', {}).get(
                        'Images', {}).get('Path', [])[0]
                    getimage = self.get_image(api_image_url, images_path, token)
        except requests.exceptions.RequestException as e:
            print(f"Error making API request: {e}")
            return {}

    def get_images_path(self, api_image_path_url, token):
        try:
            image_response = requests.get(api_image_path_url, headers={
                'Content-Type': 'application/json',
                'Accept': 'application/json',
                'Authorization': f'Bearer {token}'
            })
            image_response.raise_for_status()
            return image_response.json()
        except Exception as e:
            print(f'An error occurred while getting images path: {e}')

    def get_image(self, api_image_path_url, images_path, token, target_size_kb=200):
        try:
            url = f'{api_image_path_url}/{images_path}'
            image_response = requests.get(url, headers={
                'Content-Type': 'image/jpeg',
                'Accept': 'image/jpeg',
                'Authorization': f'Bearer {token}'
            })

            image_response.raise_for_status()
            if 'image' in image_response.headers['Content-Type']:
                image_content = image_response.content
                image_size_kb = len(image_content) / 1024.0
                print(f"Original Image size: {image_size_kb:.2f} KB")

                if image_size_kb > target_size_kb:
                    compressed_content = self.compress_image(image_content, target_size_kb)
                    self.scanned_image = base64.b64encode(compressed_content).decode('utf-8')
                    print(f"Compressed Image size: {len(compressed_content) / 1024.0:.2f} KB")
                else:
                    self.scanned_image = base64.b64encode(image_content).decode('utf-8')
                    print("No need for compression. Image size within the target.")

            else:
                print("Error: Response does not contain image data.")

        except requests.exceptions.RequestException as e:
            print(f"Error making API request for image: {e}")
            return True
    def compress_image(self, image_content, target_size_kb):
        try:
            img = Image.open(BytesIO(image_content))
            while len(image_content) / 1024.0 > target_size_kb:
                img = img.resize((int(img.width * 0.9), int(img.height * 0.9)), Image.ANTIALIAS)
                image_content = self.get_image_content(img)
            return image_content

        except Exception as e:
            print(f"Error compressing image: {e}")
            return image_content

    def get_image_content(self, image):
        # Convert the image to binary content
        buffered = BytesIO()
        image.save(buffered, format="JPEG")
        return buffered.getvalue()


class QualityPoint(models.Model):
    _inherit = "quality.point"

    dimensioner_type = fields.Selection([
        ('inner', 'Inner'),
        ('outer', 'Outer')], string='Dimensioner Type', tracking=True,
        default='', copy=False)
