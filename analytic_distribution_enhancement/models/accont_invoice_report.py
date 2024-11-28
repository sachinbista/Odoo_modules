# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields,api, models, tools


class AccountInvoiceReport(models.Model):
    _inherit = 'account.invoice.report'

    analytic_account_id = fields.Many2one(
        'account.analytic.account', string="analytic account"
    )

    product_group_id = fields.Many2one(
        'product.group',
        string="Product Group"
    )
    product_group_id_cartons = fields.Many2one(
        'product.group.carton',
        string="Product Group Cartons"
    )
    product_sub_categ_1 = fields.Many2one(
        'product.sub.category.a',
        string="Sub Category 1"
    )
    product_sub_categ_2 = fields.Many2one(
        'product.sub.category.a',
        string="Sub Category 2"
    )
    categ_id = fields.Many2one(
        'product.category',
        string="Category"
    )

    partner_state_id = fields.Many2one('res.country.state', string="Partner State")


    @api.model
    def _from(self):
        return '''
            FROM account_move_line line
                LEFT JOIN account_analytic_line analytic_line ON analytic_line.move_line_id = line.id
                LEFT JOIN res_partner partner ON partner.id = line.partner_id
                LEFT JOIN res_country_state state ON state.id = partner.state_id
                LEFT JOIN product_product product ON product.id = line.product_id
                LEFT JOIN account_account account ON account.id = line.account_id
                LEFT JOIN product_template template ON template.id = product.product_tmpl_id
                LEFT JOIN uom_uom uom_line ON uom_line.id = line.product_uom_id
                LEFT JOIN uom_uom uom_template ON uom_template.id = template.uom_id
                INNER JOIN account_move move ON move.id = line.move_id
                LEFT JOIN res_partner commercial_partner ON commercial_partner.id = move.commercial_partner_id
                LEFT JOIN ir_property product_standard_price
                    ON product_standard_price.res_id = CONCAT('product.product,', product.id)
                    AND product_standard_price.name = 'standard_price'
                    AND product_standard_price.company_id = line.company_id
                JOIN {currency_table} ON currency_table.company_id = line.company_id
        '''.format(
            currency_table=self.env['res.currency']._get_query_currency_table(self.env.companies.ids,
                                                                              fields.Date.today())
        )

    def _select(self):
        query= super(AccountInvoiceReport, self)._select() + """
            , state.id as partner_state_id
            , analytic_line.x_plan2_id as analytic_account_id
            , line.product_group_id as product_group_id
            , line.product_group_id_cartons as product_group_id_cartons
            , line.product_sub_categ_1 as product_sub_categ_1
            , line.product_sub_categ_2 as product_sub_categ_2
            , line.categ_id as categ_id

        """
        # print("selectqueryyyyy",query)
        return query

    def _group_by(self):
        query= super(AccountInvoiceReport, self)._group_by() + """
            , state.id as partner_state_id
            , analytic_line.x_plan2_id
            , line.product_group_id
            , line.product_group_id_cartons
            , line.product_sub_categ_1
            , line.product_sub_categ_2
            , line.categ_id
        """
        # print("groupbyqueryyyyy",query)
        return query
