from odoo import models
import logging
_logger = logging.getLogger(__name__)


class ProductPricelistReport(models.AbstractModel):
    _inherit = 'report.product.report_pricelist'
    
    def _get_report_data(self, data, report_type='html'):
        res = super(ProductPricelistReport, self)._get_report_data(data, report_type)
        data_pricelist_ids = data.get('pricelist_ids', [])
        if data_pricelist_ids:
            pricelists = self.env['product.pricelist'].search([('id', 'in', data_pricelist_ids)])
        else:
            pricelists = res['pricelist']
        res['pricelists'] = pricelists
        
        active_model = data.get('active_model', 'product.template')
        active_ids = data.get('active_ids') or []
        is_product_tmpl = active_model == 'product.template'
        ProductClass = self.env[active_model]

        products = ProductClass.browse(active_ids) if active_ids else ProductClass.search([('sale_ok', '=', True)])
        res['products'] = [
            self._get_pricelist_product_data(is_product_tmpl, product, pricelists, res['quantities'])
            for product in products
        ]
        return res

    def _get_pricelist_product_data(self, is_product_tmpl, product, pricelists, quantities):
        data = {
            'id': product.id,
            'name': is_product_tmpl and product.name or product.display_name,
            'price': dict.fromkeys(quantities, 0.0),
            'uom': product.uom_id.name,
        }
        for qty in quantities:
            data['price'][qty] = {
                pricelist: pricelist._get_product_price(product, qty)
                for pricelist in pricelists
            }

        if is_product_tmpl and product.product_variant_count > 1:
            data['variants'] = [
                self._get_pricelist_product_data(False, variant, pricelists, quantities)
                for variant in product.product_variant_ids
            ]

        return data