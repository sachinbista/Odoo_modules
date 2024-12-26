import base64
import re

from odoo import api, fields, models
from odoo.http import request

FONT_FAMILY_TEMPLATE = """
    @font-face {{
        font-family: {font_family};
        src: {font_src};
        font-weight: {font_weight};
        font-style: {font_style};
        font-display: {font_display};
    }}
    """
SUPPORTED_FONT_FAMILY_TYPE_FORMAT = {
    'font/woff2': "url('/web/content/{attachment_id}/{attachment_name}') format('woff2')",
    'font/woff': "url('/web/content/{attachment_id}/{attachment_name}') format('woff')",
    'application/font-woff': "url('/web/content/{attachment_id}/{attachment_name}') format('woff')",
    'application/x-font-woff': "url('/web/content/{attachment_id}/{attachment_name}') format('woff')",
    'application/x-font-ttf': "url('/web/content/{attachment_id}/{attachment_name}') format('truetype')",
    'application/x-font-opentype': "url('/web/content/{attachment_id}/{attachment_name}') format('opentype')",
    'application/vnd.ms-fontobject': "url('/web/content/{attachment_id}/{attachment_name}') format('embedded-opentype')",
    'image/svg+xml': "url('/web/content/{attachment_id}/{attachment_name}') format('svg')",
}

ENGRAVE_FONT_TEMPLATE_URL = "/bista_product_engraving/static/src/scss/engrave_font_template.scss"


class EngraveFont(models.Model):
    _name = 'engrave.font'
    _description = 'Engrave Font'

    name = fields.Char(string='Name', required=True)
    sequence = fields.Integer(string='Sequence', help="Determine the display order", index=True)
    font_url = fields.Char(string='Font URL')
    font_class = fields.Char(string='Font Class', readonly=True)
    font_attachment_ids = fields.Many2many('ir.attachment', 
                                           string='Font files', 
                                           help="Upload font file like .woff .woff2",
                                           )
    main_font_file = fields.Binary(string='Main Font File', attachment=True)

    @api.model_create_multi
    def create(self, vals_list):
        record = super(EngraveFont, self).create(vals_list)
        for rec in record:
            rec.font_class = record.name.replace(' ', '-').lower()
            if record.font_attachment_ids:
                record.font_attachment_ids.write({'public': True})
                rec.update_main_font_file()
        return record
    
    def write(self, vals):
        record = super(EngraveFont, self).write(vals)
        if 'font_attachment_ids' in vals:
            self.font_attachment_ids.write({'public': True})
            self.update_main_font_file()
        return record
    
    def unlink(self):
        record_ids = self.ids
        result = super(EngraveFont, self).unlink()
        self._update_engrave_font_template(None, record_ids)
        return result
    
    def update_main_font_file(self):
        self.ensure_one()

        for record in self:
            font_family = record.name
            font_weight = 400
            font_style = 'normal'
            font_display = 'swap'
            font_src_list = []
            for attachment in record.font_attachment_ids:
                is_supported_font_family_type = SUPPORTED_FONT_FAMILY_TYPE_FORMAT.get(attachment.mimetype)
                if is_supported_font_family_type:
                    font_src_list.append(is_supported_font_family_type.format(
                        attachment_id=attachment.id,
                        attachment_name=attachment.name,
                    ))
            font_src = ', '.join(font_src_list)
            font_family_template = None
            if font_src:
                font_family_template = FONT_FAMILY_TEMPLATE.format(
                    font_family=font_family,
                    font_src=font_src,
                    font_weight=font_weight,
                    font_style=font_style,
                    font_display=font_display,
                )
                font_family_class = """
                    .%s {
                        font-family: '%s'
                    }
                """
                font_family_class = font_family_class % (record.font_class, font_family)
                font_family_template += font_family_class
            datas = base64.encodebytes((font_family_template or "\n").encode())

            if record.main_font_file:
                record.write({
                    'main_font_file': datas,
                })
            else:
                main_font_file_attach_data = {
                    'name': font_family,
                    'datas': datas,
                    'type': 'binary',
                    'res_model': 'engrave.font',
                    'res_id': record.id,
                    'mimetype': 'text/css',
                    'public': True,
                    'res_field': 'main_font_file',
                }
                self.env['ir.attachment'].create(main_font_file_attach_data)
                self.env["ir.qweb"].clear_caches()
            self._update_engrave_font_template(font_family_template)
        return True
    
    def _update_engrave_font_template(self, font_family_template, record_ids=[]):
        """
        Update or replace content of ENGRAVE_FONT_TEMPLATE_URL
        Update web.assets_frontend
        params: font_family_template: string
        """
        WebEditorAssets = self.env["web_editor.assets"]
        IrAttachment = self.env['ir.attachment']
        if not record_ids:
            record_ids = self.ids
        for record_id in record_ids:
            main_file_content = (font_family_template or "\n")
            # replace the content in between // start_font_scss_{record.id} and // end_font_scss_{record.id}
            # with main_file_content
            custom_url = WebEditorAssets._make_custom_asset_url(ENGRAVE_FONT_TEMPLATE_URL, 'web.assets_frontend')
            engrave_font_attachment = IrAttachment.search([('url', '=', custom_url)])
            if engrave_font_attachment and not engrave_font_attachment.public:
                engrave_font_attachment.write({'public': True})
            updatedFileContent = WebEditorAssets._get_content_from_url(custom_url) or WebEditorAssets._get_content_from_url(ENGRAVE_FONT_TEMPLATE_URL)
            updatedFileContent = updatedFileContent.decode('utf-8')
            pattern = f"// start_font_scss_{record_id}.*// end_font_scss_{record_id}"
            regex = re.compile(pattern, re.DOTALL)
            replacement = f"/n// start_font_scss_{record_id}\n{main_file_content}\n// end_font_scss_{record_id}"
            if regex.search(updatedFileContent):
                updatedFileContent = re.sub(regex, replacement, updatedFileContent)
            else:
                # content will updated end of the file
                updatedFileContent += replacement
            WebEditorAssets.save_asset(ENGRAVE_FONT_TEMPLATE_URL, 'web.assets_frontend', updatedFileContent, 'scss')
        # self.env['ir.qweb']._get_asset_link_urls('web.assets_frontend', request.session.debug)
        self.env["ir.qweb"].clear_caches()






