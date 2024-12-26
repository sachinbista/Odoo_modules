from odoo import models, fields, api, _
import requests
import base64
from odoo.exceptions import UserError
import re

try:
    from zebrafy import ZebrafyImage
except Exception as e:
    print("Log======================================")
    print(e)
import base64
import io
from PIL import Image
from datetime import datetime, date, timedelta
from dateutil import relativedelta


class ZplLabel(models.Model):
    _name = "zpl.label"
    _description = "Print Label"

    name = fields.Char()
    model = fields.Selection([
        ('product.template', 'Product'),
        ('stock.lot', 'Lot/Serial'),
        ('stock.move.line', 'Stock Move'),
        ('stock.location', 'Location'),
        ('stock.picking', 'Stock Picking')], default="product.template")

    product_label = fields.Many2one('zpl.label', copy=True)
    lot_label = fields.Many2one('zpl.label', copy=True)
    label = fields.Text(copy=True, compute="_preview")
    barcode_preview = fields.Binary(compute="_preview")
    barcode_preview_serial = fields.Binary(compute="_preview")

    width = fields.Float(default=2)
    height = fields.Float(default=1)
    dpi = fields.Selection([("6", "152 Dpi"), ("8", "203 Dpi"), ("12", "300 Dpi"), ("24", "600 Dpi")],
                           default="12")
    margin_left = fields.Float(copy=True)
    margin_top = fields.Float(copy=True)
    qrcode_field_ids = fields.One2many('label.field', 'label_id', domain=[('name', '=', 'qrcode')])
    text_field_ids = fields.One2many('label.field', 'label_id', domain=[('name', '=', 'text')])
    multiline_field_ids = fields.One2many('label.field', 'label_id', domain=[('name', '=', 'multiline')])
    label_ids = fields.One2many('label.field', 'label_id', domain=[('name', '=', 'label')])
    border_ids = fields.One2many('label.field', 'label_id', domain=[('name', '=', 'border')])
    model_id = fields.Many2one('ir.model')
    label_field_ids = fields.One2many('label.field', 'label_id', copy=True)
    product_id = fields.Many2one('product.template')
    serial_id = fields.Many2one('stock.lot')
    move_id = fields.Many2one('stock.move.line')
    location_id = fields.Many2one('stock.location')
    move_type = fields.Selection([('product.template', 'Product'), ('stock.lot', 'Lot/Serial')])
    group_ids = fields.Many2many('res.groups')
    user_ids = fields.Many2many('res.users', compute="_compute_user_ids", store=True)
    image_ids = fields.One2many('label.field', 'label_id', domain=[('name', '=', 'image')])
    zpl_blue = fields.Html()

    @api.depends("group_ids.users")
    def _compute_user_ids(self):
        for x in self:
            user_ids = []
            for group in x.group_ids:
                user_ids += group.users.ids
            x.user_ids = [(6, 0, user_ids)]

    @api.onchange("move_id")
    def _get_move_type(self):
        if self.move_id.sudo():
            if self.move_id.lot_id:
                self.move_type = "stock.lot"
            else:
                self.move_type = "product.template"

    def name_get(self):
        res = []
        for label in self:
            if label.width and label.height:
                res.append((label.id, _(f'{label.name} ({label.height}/{label.width} in)')))
            else:
                res.append((label.id, _('%s') % label.name))
        return res

    def get_diff(self, old, new):
        diff_percentage = (new / (old or 1))
        return diff_percentage

    @api.onchange("model")
    def _get_model(self):
        if self.model:
            model_id = self.env['ir.model'].sudo().search([('model', '=', self.model)], limit=1)
            if model_id:
                self.model_id = model_id

    @api.onchange("height", "width")
    def _update_label_size(self):
        if self.width == self._origin.width and self.height == self._origin.height:
            return

        width_diff = self.get_diff(self._origin.width, self.width)
        height_diff = self.get_diff(self._origin.height, self.height)

        for rec in self.label_field_ids:
            if width_diff:
                rec.left = (rec.left * width_diff)
                if rec.name == "border":
                    rec.right = (rec.right + width_diff)

                rec.max_width = (rec.max_width * width_diff)
                rec.max_length = (rec.max_length * width_diff)

            if height_diff:
                rec.top = (rec.top * height_diff)
                if rec.name == "border":
                    rec.bottom = (rec.bottom * height_diff)

            rec.font_size = rec.font_size * width_diff
            if rec.magnification:
                magnification = round((int(rec.magnification) * width_diff))
                if magnification > 10:
                    magnification = 10
                elif magnification < 1:
                    magnification = 1
                else:
                    magnification = magnification
                rec.magnification = str(magnification)

    def _get_label_date(self, record=None):
        field_data = []
        for line in self.label_field_ids:
            data = line._get_line(record=record)
            if not data:
                continue
            field_data.append(data)
        if not field_data:
            return ""
        return f"""
                ^XA
                    {"".join(field_data)}
                ^XZ
                """



    @api.depends("label_field_ids", "text_field_ids",
                 "multiline_field_ids", "qrcode_field_ids",
                 "height", "width",
                 "dpi", "margin_left",
                 "margin_top")
    def _preview(self):
        for x in self.sudo():
            if x.model == 'stock.picking':
                if x.product_label:
                    x.product_label._preview()
                    x.barcode_preview = x.product_label.barcode_preview
                if x.lot_label:
                    x.lot_label._preview()
                    x.barcode_preview_serial = x.lot_label.barcode_preview
                x.label = ""
                return

            x.label = x._get_label_date()

            if not x.height:
                raise UserError("Invalid label Height.")
            if not x.width:
                raise UserError("Invalid label Width.")

            barcode_preview = False
            barcode_preview_serial = False

            if x.label:
                url = f'http://api.labelary.com/v1/printers/{x.dpi}dpmm/labels/{x.width}x{x.height}/0/ '
                files = {'file': x.label}
                headers = {'Accept': 'image/png'}  # omit this line to get PNG images back
                response = requests.post(url, headers=headers, files=files, stream=True)
                if response.status_code == 200:
                    barcode_preview = base64.b64encode(response.content)
                    barcode_preview_serial = base64.b64encode(response.content)
            x.barcode_preview = barcode_preview
            x.barcode_preview_serial = barcode_preview_serial
            return x.label

    @api.model
    def get_zpl(self, raw, dpi, width, height):
        url = f'http://api.labelary.com/v1/printers/{dpi}dpmm/labels/{width}x{height}/0/ '
        files = {'file': raw}
        headers = {'Accept': 'image/png'}  # omit this line to get PNG images back
        response = requests.post(url, headers=headers, files=files, stream=True)
        if response.status_code == 200:
            return base64.b64encode(response.content)
        return ""

    def write(self, vals):
        ret = super(ZplLabel, self).write(vals)
        return ret


class LabelFields(models.Model):
    _name = 'label.field'

    name = fields.Selection(
        [('qrcode', 'QR Code'), ('text', 'Text'), ('label', 'Label'),
         ('multiline', 'Multi Line Text'), ('border', 'Border/Line'), ('image', 'Image')], required=True)
    top = fields.Integer()
    left = fields.Integer()
    right = fields.Integer()
    bottom = fields.Integer()
    border_width = fields.Integer()

    font_size = fields.Integer(default=30)
    max_length = fields.Integer()
    label = fields.Char()
    model_id = fields.Many2one('ir.model', related="label_id.model_id")
    value = fields.Many2one("ir.model.fields", string="Value Source")
    magnification = fields.Selection([
        ("1", "1"),
        ("2", "2"),
        ("3", "3"),
        ("4", "4"),
        ("5", "5"),
        ("6", "6"),
        ("7", "7"),
        ("8", "8"),
        ("9", "9"),
        ("10", "10"),
    ], default="7")
    max_width = fields.Integer()
    max_line = fields.Integer()
    label_id = fields.Many2one('zpl.label')
    color = fields.Integer()
    related_field = fields.Many2one('ir.model.fields')
    field_model_id = fields.Many2one('ir.model')
    attachment = fields.Binary()
    font = fields.Selection([("A", "Type A"),
                             ("B", "Type B"),
                             ("C", "Type C"),
                             ("D", "Type D"),
                             ("E", "Type E"),
                             ("F", "Type F"),
                             ("G", "Type G"),
                             ("H", "Type H"),
                             ("0", "Default"),
                             ("GS", "TYPE GS"),
                             ("P", "TYPE P"),
                             ("Q", "TYPE Q"),
                             ("R", "TYPE R"),
                             ("S", "TYPE S"),
                             ("T", "TYPE T"),
                             ("U", "TYPE U"),
                             ("V", "TYPE V")],
                            default="0", help="Refer to 'FONT TYPE' tab for each font type description.")

    @api.onchange("name", "top", "left", "right", "bottom", "border_width", "font_size", "max_length", "label",
                  "model_id", "value", "magnification", "max_width", "max_line", "label_id", "color", "related_field",
                  "field_model_id", "attachment", "font")
    def _onchange_update_label(self):
        self._get_line()

    def write(self, vals):
        print("Label ", self.label_id)
        print("Write ", vals)
        return super(LabelFields, self).write(vals)

    @api.onchange("value")
    def _get_field_attributes(self):
        for x in self.sudo():
            if not x.value:
                continue

            x.label = x.value.field_description
            if x.value.ttype == "many2one":
                x.field_model_id = x.env['ir.model'].search([('model', '=', x.value.relation)], limit=1)
            if x.name == "multiline":
                if not x.max_width:
                    x.max_width = x.label_id.width * 250
                if not x.max_line:
                    x.max_line = 2

    def _get_line(self, record=None):
        label = self.label_id
        value = False
        if self.value:
            if record:
                value = self._get_value(record)
            elif label.model == 'product.template' and label.product_id:
                value = self._get_value(label.product_id)
            elif label.model == "stock.lot" and label.serial_id:
                value = self._get_value(label.serial_id)
            elif label.model == "stock.move.line" and label.move_id:
                value = self._get_value(label.move_id)
            elif label.model == 'stock.location' and label.location_id:
                value = self._get_value(label.location_id)
        if not value:
            value = ""

        left = self.left + label.margin_left
        right = self.right + label.margin_left
        top = self.top + label.margin_top
        bottom = self.bottom + label.margin_top

        if self.name == "qrcode":
            return f"^FO{left},{top}^BQN,2,{self.magnification},M,7^FDQA,{value}^FS"
        elif self.name in ['text', 'label']:
            wild_card = self.label or ''
            if "{" in wild_card and "}" in wild_card:
                wild_card = wild_card.replace("{", "").replace("}", "")
                code_list = wild_card.split(".")
                prefix = code_list[0] if len(code_list) else False
                if prefix and prefix in ['date','datetime','relativedelta', 'timedelta']:
                    try:
                        wild_card = eval(wild_card)
                    except Exception as e:
                        wild_card = ''

            return f"^FO{left},{top}^A{self.font},{self.font_size}^FD{wild_card or ''}{value}^FS"
        elif self.name == 'multiline':
            return f"^FO{left},{top}^A{self.font},{self.font_size}^FB{self.max_width},{self.max_line},10,L^FD{self.label or ''}{value}^FS"
        elif self.name == "border":
            return f"^FO{left},{top}^GB{right},{bottom},{self.border_width}^FS"
        elif self.name == 'image' and self.attachment:
            zpl_string = self.process_image(self.attachment.decode('utf-8'))
            return zpl_string

    def process_image(self, input_data):
        if isinstance(input_data, str):
            input_data = base64.b64decode(input_data)
        elif not isinstance(input_data, bytes):
            raise ValueError("Input must be either bytes or a Base64-encoded string")

        # Create a BytesIO object to simulate a file-like object
        image_stream = io.BytesIO(input_data)
        image = Image.open(image_stream)

        # Process the image using ZebrafyImage or any other logic
        zpl_string = ZebrafyImage(image,
                                  compression_type="A",
                                  invert=True,
                                  # threshold=240,
                                  width=self.right,
                                  height=self.bottom,
                                  complete_zpl=False,
                                  pos_x=self.left,
                                  pos_y=self.top
                                  ).to_zpl()
        return zpl_string

    def _get_value(self, record):
        value = record[self.value.name]
        field = self.value
        if self.related_field:
            value = value[self.related_field.name]
            field = self.related_field
        if value:
            if field.ttype == "many2one":
                value = value.display_name
            elif field.ttype in ["many2many", "one2many"]:
                value = ", ".join([line.display_name for line in value])
            elif field.ttype == "html":
                text = re.compile('<.*?>')
                value = re.sub(text, '', str(value)) or ""
            if self.max_length:
                value = value[:self.max_length]
        return value

    @api.model
    def create(self, vals_list):
        ret = super(LabelFields, self).create(vals_list)
        if ret.label_id:
            ret.label_id._preview()
        return ret
