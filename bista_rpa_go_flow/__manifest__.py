# -*- coding: utf-8 -*-
{
    "name": "Bista Go FLow Automation.",
    "version": "16.0.0",
    "author": "Bista Solutions",
    "website": "https://www.bistasolutions.com",
    "category": "Delivery",
    "license": "LGPL-3",
    "support": "  ",
    "summary": "API Integration",
    "description": """API Integration.""",
    "depends": [
        'bista_go_flow'
    ],
    "data": [
        'security/ir.model.access.csv',
        'data/automation_schedule_action.xml',
        'views/go_flow_packaging_update_log.xml',
        'views/flaskserver_config_view.xml'
    ],
    "application": True,
    "installable": True,
    "auto_install": False,
}
