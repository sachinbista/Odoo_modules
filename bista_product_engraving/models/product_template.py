from odoo import models, fields


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    def _default_minimum_charges(self):
        # TODO: fetch from settings
        return 30.0
    
    def _default_minimum_charges_char_limit(self):
        # TODO: fetch from settings
        return 12
    
    has_engrave_feature = fields.Boolean(string='Has Engrave Feature?')
    minimum_charges = fields.Float(string='Minimum Charges', digits='Product Price', default=_default_minimum_charges)
    minimum_charges_char_limit = fields.Integer(string='Minimum Charges Character Limit', default=_default_minimum_charges_char_limit)
    charges_per_char = fields.Float(string='Charges Per Character', digits='Product Price', default=2.5)
    max_char_limit = fields.Integer(string='Max Character Limit', default=30)
    restrict_font_ids = fields.Many2many('engrave.font', string='Exclude Fonts')

    def _get_combination_info(self, combination=False, product_id=False, add_qty=1, pricelist=False, parent_combination=False, only_template=False):
        combination_info = super()._get_combination_info(combination=combination, product_id=product_id, add_qty=add_qty, pricelist=pricelist, parent_combination=parent_combination, only_template=only_template)
        EngraveFont = self.env['engrave.font']
        product_variant_id = self.env['product.product'].browse(combination_info['product_id'])
        available_font_ids = EngraveFont.search([('id', 'not in', product_variant_id.restrict_font_ids.ids)])

        combination_info.update({
            'has_engrave_feature': product_variant_id.has_engrave_feature,
            'minimum_charges': product_variant_id.minimum_charges,
            'minimum_charges_char_limit': product_variant_id.minimum_charges_char_limit,
            'charges_per_char': product_variant_id.charges_per_char,
            'max_char_limit': product_variant_id.max_char_limit,
            'available_font_ids': available_font_ids,
        })

        tooltip_title = '≤ {} letters: {} ,+ {} per extra letters. </br> ( Max allowed letters: {} )'.format(
            combination_info['minimum_charges_char_limit'],
            combination_info['minimum_charges'],
            combination_info['charges_per_char'],
            combination_info['max_char_limit'],
        )
        combination_info.update({
            'tooltip_title': tooltip_title,
        })
        return combination_info
    

class ProductProduct(models.Model):
    _inherit = 'product.product'

    def calculate_engrave_charges(self, engrave_text):
        """
        Calculate engrave charges based on product's minimum charges, minimum charges character limit and charges per char
        :param engrave_text: string
        :return: float
        """
        self.ensure_one()
        engrave_text = engrave_text.strip()
        minimum_charges_char_limit = self.minimum_charges_char_limit
        minimum_charges = self.minimum_charges
        charges_per_char = self.charges_per_char
        if len(engrave_text) <= minimum_charges_char_limit:
            return minimum_charges
        else:
            return minimum_charges + (len(engrave_text) - minimum_charges_char_limit) * charges_per_char
        