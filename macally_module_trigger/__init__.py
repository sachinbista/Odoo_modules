# -*- coding: utf-8 -*-

from . import models

def post_init_hook_config(env):
    group_user = env.ref('base.group_user')
    group_product_variants = env.ref('product.group_product_variant')
    group_product_pricelists = env.ref('product.group_product_pricelist')
    group_stock_multi_locations_config = env.ref('stock.group_stock_multi_locations')
    group_stock_adv_location = env.ref('stock.group_adv_location')
    group_analytic_account = env.ref('analytic.group_analytic_accounting')

    groups_to_add = [
        (4, group_product_pricelists.id),
        (4, group_product_variants.id),
        (4, group_stock_multi_locations_config.id),
        (4, group_stock_adv_location.id),
        (4, group_analytic_account.id)
    ]
    group_user.write({'implied_ids': groups_to_add})
