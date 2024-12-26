from odoo import fields, models
import pytz
import logging

_logger = logging.getLogger(__name__)
class ProductsCleanUp(models.TransientModel):
    _name = 'products.cleanup'
    _description = 'Products Cleanup'

    date_from = fields.Datetime(string='Date From')
    date_to = fields.Datetime(string='Date To')
    product_categories = fields.Many2many(string='Product Categories',comodel_name='product.category')
    lbl_message = fields.Boolean(string='Message')

    def get_date_with_tz(self, date):
        datetime_with_tz = pytz.timezone(self._context['tz']).localize(fields.Datetime.from_string(date),is_dst=None)
        datetime_in_utc = datetime_with_tz.astimezone(pytz.utc)
        date = datetime_in_utc.strftime('%Y-%m-%d %H:%M:%S')
        return date

    def products_cleanup(self):
        date_from = self.get_date_with_tz(self.date_from)
        date_to = self.get_date_with_tz(self.date_to)

        products = self.env['product.template'].search([('create_date','>=',date_from),('create_date','<=',date_to),('categ_id','in',self.product_categories.ids)])

        for prod in products:
            products_variants = self.env['product.product'].search([('product_tmpl_id','=',prod.id)])
            products_variants_str = ','.join(str(x) for x in products_variants.ids)
            products_variants_ids = '(' + products_variants_str + ')'

            var_sql = ''
            for var in products_variants:
                var_sql+='and pp.id = %s  '%(var.id)

            check_transactions_sql = ''' SELECT DISTINCT(pt.id) FROM product_product pp
                
                INNER JOIN product_template pt ON (pp.product_tmpl_id = pt.id)
                LEFT JOIN stock_move_line sml ON (sml.product_id = pp.id)
                LEFT JOIN sale_order_line sol ON (sol.product_id = pp.id)
                LEFT JOIN account_invoice_line ail ON (ail.product_id = pp.id)
                LEFT JOIN purchase_order_line pol ON (pol.product_id = pp.id)
                LEFT JOIN stock_inventory_line sil ON (sil.product_id = pp.id)
                LEFT JOIN account_move_line aml ON (aml.product_id = pp.id)
            
                WHERE sml.product_id IS NULL and sol.product_id IS NULL and 
                pol.product_id IS NULL and ail.product_id IS NULL and sil.product_id IS NULL and aml.product_id IS NULL
                and pt.create_date>='%s' and pt.create_date<='%s' ''' %(date_from,date_to)
            check_transactions_sql+=var_sql

            self._cr.execute(check_transactions_sql)
            result = self._cr.dictfetchall()

            if result:
                delete_sql = '''DELETE FROM product_template where id = %s ;''' %(result[0].get('id'))
                _logger.info('Product Sku %s Has Been Deleted Permanently'%prod.default_code)

                self._cr.execute(delete_sql)
                self._cr.commit()

        wizard_form = self.env.ref('products_cleanup.products_cleanup_form', False)
        view_id = self.env['products.cleanup']
        vals = {
            'date_from': date_from,
            'date_to' : date_to,
            'product_categories' : [(6,0,self.product_categories.ids)],
            'lbl_message' : True
        }
        new = view_id.create(vals)
        return {
            'name': ('Products Cleanup'),
            'type': 'ir.actions.act_window',
            'res_model': 'products.cleanup',
            'res_id': new.id,
            'view_id': wizard_form.id,
            'view_type': 'form',
            'view_mode': 'form',
            'target': 'new'
        }