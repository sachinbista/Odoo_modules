# Copyright 2020 Tecnativa - Manuel Calero
# Copyright 2022 Quartile
# Copyright 2014-2022 Tecnativa - Pedro M. Baeza
{
    "name": "Commissions",
    "version": "16.0.1.2.0",
    "author": "Tecnativa, Odoo Community Association (OCA)",
    "category": "Invoicing",
    "license": "AGPL-3",
    "depends": ['product', 'account_reports', 'bista_freight_charges'],
    "website": "https://github.com/OCA/commission",
    "maintainers": ["pedrobaeza"],
    "data": [
        "security/commission_security.xml",
        "security/ir.model.access.csv",
        "data/menuitem_data.xml",
        "data/agent_commission_report.xml",
        'wizards/agent_commission_report_wizard_view.xml',
        "views/commission_views.xml",
        "views/agent_commission_reports_view.xml",
        "views/commission_settlement_views.xml",
        "views/commission_mixin_views.xml",
        "views/product_template_views.xml",
        "views/res_partner_views.xml",
        # "views/report_menu_action.xml",
        "views/report_filter_view.xml",
        "views/account_report_view.xml",
        "reports/commission_settlement_report.xml",
        "reports/report_settlement_templates.xml",
        "wizards/commission_make_settle_views.xml",
    ],
    'assets': {
        'web.assets_backend': [
            'commission/static/src/js/account_reports.js',
        ],
    },
    "demo": ["demo/commission_and_agent_demo.xml"],
    "installable": True,
}
