# Copyright 2015-2016 Pedro M. Baeza <pedro.baeza@tecnativa.com>
# License AGPL-3 - See http://www.gnu.org/licenses/agpl-3.0.html

import logging

from odoo import SUPERUSER_ID, api

_logger = logging.getLogger(__name__)

# try:
#     from odoo.addons.base_multi_company import hooks
# except ImportError:
#     _logger.info("Cannot find `base_multi_company` module in addons path.")


def post_init_hook(env):
    ir_model_data = env['ir.model.data'].search(
        [('name', '=', 'product_comp_rule'), ('module', '=', 'product')])
    ir_model_data.sudo().write({'noupdate': False})

    record = env[ir_model_data.model].browse(ir_model_data.res_id)
    record.sudo().write({
        "active": True,
        "domain_force": "['|', ('company_ids', '=', False),('company_ids', 'in', company_ids)]"
    })

    ir_model_data.write({'noupdate': True})


def uninstall_hook(env):
    """Restore rule to base value.

    Args:
        env (Environment): Environment to use for operation.
        rule_ref (string): XML ID of security rule to remove the
            `domain_force` from.
    """
    # Change access rule
    ir_model_data = env['ir.model.data'].search(
        [('name', '=', 'product_comp_rule'), ('module', '=', 'product')])
    ir_model_data.sudo().write({'noupdate': False})
    rule = env.ref("product.product_comp_rule")
    # rule = env.ref(rule_ref)
    if rule:  # safeguard if it's deleted
        rule.write(
            {
                "active": True,
                "domain_force": "['|', ('company_id', 'parent_of', company_ids), ('company_id', '=', False)]",
            }
        )
    ir_model_data.write({'noupdate': True})
