# Copyright 2015 Noviat.
# License LGPL-3 or later (https://www.gnu.org/licenses/lgpl).

{
    "name": "EBICS Banking Protocol",
    "summary": (
        "Download bank statements and upload payment files directly from Odoo, "
        "using the European EBICS standard"
    ),
    "version": "18.0.1.2.2",
    "license": "LGPL-3",
    "author": "Noviat",
    "website": "https://www.noviat.com/",
    "category": "Accounting & Finance",
    "depends": ["account"],
    "data": [
        "security/ebics_security.xml",
        "security/ir.model.access.csv",
        "data/ebics_file_format.xml",
        "views/ebics_config_views.xml",
        "views/ebics_file_views.xml",
        "views/ebics_userid_views.xml",
        "views/ebics_file_format_views.xml",
        "wizards/ebics_change_passphrase.xml",
        "wizards/ebics_xfer.xml",
        "wizards/ebics_admin_order.xml",
        "views/menu.xml",
    ],
    "installable": True,
    "application": True,
    "external_dependencies": {
        "python": [
            "fintech",
            "cryptography",
        ]
    },
    "images": ["static/description/banner.png"],
}
