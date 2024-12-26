{
    "name": "Bista Report to printer Extension",
    "version": "1.0",
    "category": "Generic Modules/Base",
    "author": "Omid Totakhel @ Bistasolutions.com",
    "website": "https://bistasolutions.com",
    "license": "AGPL-3",
    "depends": ["web", "base_report_to_printer", "bista_zpl_labels"],
    "data": [
        "security/security.xml",
        "views/printing_printer.xml",
        "views/print_wizard.xml",
    ],
    "assets": {},
    "installable": True,
    "application": False,
    "external_dependencies": {"python": ["pycups"]},
}
