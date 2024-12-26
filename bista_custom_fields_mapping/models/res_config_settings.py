# -*- coding: utf-8 -*-
# License AGPL-3
from odoo import api, fields, models

GMAPS_LANG_LOCALIZATION = [
    ('af', 'Afrikaans'),
    ('ja', 'Japanese'),
    ('sq', 'Albanian'),
    ('kn', 'Kannada'),
    ('am', 'Amharic'),
    ('kk', 'Kazakh'),
    ('ar', 'Arabic'),
    ('km', 'Khmer'),
    ('ar', 'Armenian'),
    ('ko', 'Korean'),
    ('az', 'Azerbaijani'),
    ('ky', 'Kyrgyz'),
    ('eu', 'Basque'),
    ('lo', 'Lao'),
    ('be', 'Belarusian'),
    ('lv', 'Latvian'),
    ('bn', 'Bengali'),
    ('lt', 'Lithuanian'),
    ('bs', 'Bosnian'),
    ('mk', 'Macedonian'),
    ('bg', 'Bulgarian'),
    ('ms', 'Malay'),
    ('my', 'Burmese'),
    ('ml', 'Malayalam'),
    ('ca', 'Catalan'),
    ('mr', 'Marathi'),
    ('zh', 'Chinese'),
    ('mn', 'Mongolian'),
    ('zh-CN', 'Chinese (Simplified)'),
    ('ne', 'Nepali'),
    ('zh-HK', 'Chinese (Hong Kong)'),
    ('no', 'Norwegian'),
    ('zh-TW', 'Chinese (Traditional)'),
    ('pl', 'Polish'),
    ('hr', 'Croatian'),
    ('pt', 'Portuguese'),
    ('cs', 'Czech'),
    ('pt-BR', 'Portuguese (Brazil)'),
    ('da', 'Danish'),
    ('pt-PT', 'Portuguese (Portugal)'),
    ('nl', 'Dutch'),
    ('pa', 'Punjabi'),
    ('en', 'English'),
    ('ro', 'Romanian'),
    ('en-AU', 'English (Australian)'),
    ('ru', 'Russian'),
    ('en-GB', 'English (Great Britain)'),
    ('sr', 'Serbian'),
    ('et', 'Estonian'),
    ('si', 'Sinhalese'),
    ('fa', 'Farsi'),
    ('sk', 'Slovak'),
    ('fi', 'Finnish'),
    ('sl', 'Slovenian'),
    ('fil', 'Filipino'),
    ('es', 'Spanish'),
    ('fr', 'French'),
    ('es-419', 'Spanish (Latin America)'),
    ('fr-CA', 'French (Canada)'),
    ('sw', 'Swahili'),
    ('gl', 'Galician'),
    ('sv', 'Swedish'),
    ('ka', 'Georgian'),
    ('ta', 'Tamil'),
    ('de', 'German'),
    ('te', 'Telugu'),
    ('el', 'Greek'),
    ('th', 'Thai'),
    ('gu', 'Gujarati'),
    ('tr', 'Turkish'),
    ('iw', 'Hebrew'),
    ('uk', 'Ukrainian'),
    ('hi', 'Hindi'),
    ('ur', 'Urdu'),
    ('hu', 'Hungarian'),
    ('uz', 'Uzbek'),
    ('is', 'Icelandic'),
    ('vi', 'Vietnamese'),
    ('id', 'Indonesian'),
    ('zu', 'Zulu'),
    ('it', 'Italian'),
]


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    @api.model
    def get_region_selection(self):
        country_ids = self.env['res.country'].search([])
        values = [(country.code, country.name) for country in country_ids]
        return values

    google_maps_view_api_key = fields.Char(string='Google Maps View Api Key')
    google_maps_lang_localization = fields.Selection(
        selection=GMAPS_LANG_LOCALIZATION,
        string='Google Maps Language Localization')
    google_maps_region_localization = fields.Selection(
        selection=get_region_selection,
        string='Google Maps Region Localization')
    google_maps_theme = fields.Selection(
        selection=[('default', 'Default'),
                   ('aubergine', 'Aubergine'),
                   ('night', 'Night'),
                   ('dark', 'Dark'),
                   ('retro', 'Retro'),
                   ('silver', 'Silver')],
        string='Map theme')
    google_maps_places = fields.Boolean(string='Places', default=True)
    google_maps_geometry = fields.Boolean(string='Geometry', default=True)
    google_maps_libraries = fields.Char(
        string='Libraries',
        config_parameter='web_google_maps.libraries')
    google_autocomplete_lang_restrict = fields.Boolean(
        string='Google Autocomplete Language Restriction',
        config_parameter='web_google_maps.autocomplete_lang_restrict')

    repair_gross_margin_max_percentage = fields.Float(string='Repair Gross Margin Max Percentage',
                                                      config_parameter='repair_gross_margin_max_percentage')
    service_gross_margin_max_percentage = fields.Float(string='Service Gross Margin Max Percentage',
                                                       config_parameter='service_gross_margin_max_percentage')
    additional_cogs_percentage = fields.Float(string='Additional COGS Percentage',
                                              config_parameter='additional_cogs_percentage')
    facebook_sharing = fields.Boolean(string='Facebook', related='website_id.facebook_sharing',readonly=False)
    twitter_sharing = fields.Boolean(string='Twitter', related='website_id.twitter_sharing', readonly=False)
    linkedin_sharing = fields.Boolean(string='Linkedin', related='website_id.linkedin_sharing', readonly=False)
    mail_sharing = fields.Boolean(string='Mail', related='website_id.mail_sharing', readonly=False)
    is_load_more = fields.Boolean(string='Load More', related='website_id.is_load_more', readonly=False,
                                  help="Load next page products with Ajax")
    load_more_image = fields.Binary(string='Load More Image', related='website_id.load_more_image', readonly=False,
                                    help="Display this image while load more applies.")
    button_or_scroll = fields.Selection(related='website_id.button_or_scroll',
                                        required=True, readonly=False,
                                        help="Define how to show the pagination of products in a shop page with on scroll or button.")
    prev_button_label = fields.Char(string='Label for the Prev Button', related='website_id.prev_button_label',
                                    readonly=False, translate=True)
    next_button_label = fields.Char(string='Label for the Next Button', related='website_id.next_button_label',
                                    readonly=False, translate=True)
    number_of_product_line = fields.Selection(related='website_id.number_of_product_line',
                                              string="Number of lines for product name",
                                              readonly=False, help="Number of lines to show in product name for shop.")
    is_auto_play = fields.Boolean(string='Slider Auto Play', related='website_id.is_auto_play', default=True,
                                  readonly=False)

    is_pwa = fields.Boolean(string='PWA', related='website_id.is_pwa', readonly=False, help="Pwa will be enabled.")
    pwa_name = fields.Char(string='Name', related='website_id.pwa_name', readonly=False)
    pwa_short_name = fields.Char(string='Short Name', related='website_id.pwa_short_name', readonly=False)
    pwa_theme_color = fields.Char(string='Theme Color', related='website_id.pwa_theme_color', readonly=False)
    pwa_bg_color = fields.Char(string='Background Color', related='website_id.pwa_bg_color', readonly=False)
    pwa_start_url = fields.Char(string='Start URL', related='website_id.pwa_start_url', readonly=False)
    app_image_512 = fields.Binary(string='Application Image(512x512)', related='website_id.app_image_512',
                                  readonly=False)

    is_price_range_filter = fields.Boolean(string='Price Range Filter', related='website_id.is_price_range_filter',
                                           readonly=False, help="Enable the price range filter")
    price_filter_on = fields.Selection(related='website_id.price_filter_on',
                                       readonly=False)
    cancel_done_picking = fields.Boolean(string='Cancel Done Delivery?')
    check_selection = fields.Selection([
        ('blank_check', 'Blank Check'),
        ('pre_printed_check', 'Pre Printed Check')], string="Check Type", default='blank_check')
    google_api_key = fields.Char('Google API key')


    @api.onchange('google_maps_lang_localization')
    def onchange_lang_localization(self):
        if not self.google_maps_lang_localization:
            self.google_maps_region_localization = ''

    def set_values(self):
        super(ResConfigSettings, self).set_values()
        ICPSudo = self.env['ir.config_parameter'].sudo()
        lang_localization = self._set_google_maps_lang_localization()
        region_localization = self._set_google_maps_region_localization()

        lib_places = self._set_google_maps_places()
        lib_geometry = self._set_google_maps_geometry()

        active_libraries = '%s,%s' % (lib_geometry, lib_places)

        ICPSudo.set_param('google.api_key_geocode',
                          self.google_maps_view_api_key)
        ICPSudo.set_param('google.lang_localization',
                          lang_localization)
        ICPSudo.set_param('google.region_localization',
                          region_localization)
        ICPSudo.set_param('google.maps_theme', self.google_maps_theme)
        ICPSudo.set_param('google.maps_libraries', active_libraries)
        ICPSudo.set_param('bista_custom_fields_mapping.check_selection',
                  self.check_selection)
        ICPSudo.set_param('bista_custom_fields_mapping.google_api_key',
                                                         self.google_api_key)
        company_id = self.env.user.company_id
        company_id.cancel_done_picking = self.cancel_done_picking

    @api.model
    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        ICPSudo = self.env['ir.config_parameter'].sudo()

        lang_localization = self._get_google_maps_lang_localization()
        region_localization = self._get_google_maps_region_localization()

        lib_places = self._get_google_maps_places()
        lib_geometry = self._get_google_maps_geometry()

        res.update({
            'google_maps_view_api_key': ICPSudo.get_param(
                'google.api_key_geocode', default=''),
            'google_maps_lang_localization': lang_localization,
            'google_maps_region_localization': region_localization,
            'google_maps_theme': ICPSudo.get_param(
                'google.maps_theme', default='default'),
            'google_maps_places': lib_places,
            'google_maps_geometry': lib_geometry,
            'cancel_done_picking' : self.env.user.company_id.cancel_done_picking
        })
        res['check_selection'] = (
            self.env['ir.config_parameter'].sudo().get_param('bista_custom_fields_mapping.check_selection',
                                                             default=0))
        res['google_api_key'] = (
            self.env['ir.config_parameter'].sudo().get_param('bista_custom_fields_mapping.google_api_key',
                                                             default=0))
        return res

    def _set_google_maps_lang_localization(self):
        if self.google_maps_lang_localization:
            lang_localization = '&language=%s' % \
                                self.google_maps_lang_localization
        else:
            lang_localization = ''

        return lang_localization

    @api.model
    def _get_google_maps_lang_localization(self):
        ICPSudo = self.env['ir.config_parameter'].sudo()
        google_maps_lang = ICPSudo.get_param(
            'google.lang_localization', default='')
        val = google_maps_lang.split('=')
        lang = val and val[-1] or ''
        return lang

    def _set_google_maps_region_localization(self):
        if self.google_maps_region_localization:
            region_localization = '&region=%s' % \
                                  self.google_maps_region_localization
        else:
            region_localization = ''

        return region_localization

    @api.model
    def _get_google_maps_region_localization(self):
        ICPSudo = self.env['ir.config_parameter'].sudo()
        google_maps_region = ICPSudo.get_param(
            'google.region_localization', default='')
        val = google_maps_region.split('=')
        region = val and val[-1] or ''
        return region

    @api.model
    def _get_google_maps_geometry(self):
        ICPSudo = self.env['ir.config_parameter'].sudo()
        google_maps_libraries = ICPSudo.get_param(
            'google.maps_libraries', default='')
        libraries = google_maps_libraries.split(',')
        return 'geometry' in libraries

    def _set_google_maps_geometry(self):
        return 'geometry' if self.google_maps_geometry else ''

    @api.model
    def _get_google_maps_places(self):
        ICPSudo = self.env['ir.config_parameter'].sudo()
        google_maps_libraries = ICPSudo.get_param(
            'google.maps_libraries', default='')
        libraries = google_maps_libraries.split(',')
        return 'places' in libraries

    def _set_google_maps_places(self):
        return 'places' if self.google_maps_places else ''