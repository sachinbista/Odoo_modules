

{
    'name': 'Vendor Approval',
    "version": "1.8",
    "license": "AGPL-3",
    "author": "Bista Solutions",
    "website": "http://www.bistasolutions.com",
    'description': """ Vendor Approval functionality (1. Send for Approval and 2. Approved to Pay) for Vendor Invoice
    """,
    'depends': [
        'account_check_printing'
    ],
    'data': [
             'security/vendor_security.xml',
             'security/ir.model.access.csv',
            'wizard/invoice_approval_wizard_view.xml',
            'views/vendor_approval_view.xml',
            # 'views/action_approval_views.xml',
            ],
    "demo": [],
    "test": [],
    'installable': True,
    'auto_install': False,
    "images": [],
}
