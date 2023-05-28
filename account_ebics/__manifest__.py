# Copyright 2009-2023 Noviat.
# License AGPL-3 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "EBICS banking protocol",
    "version": "16.0.1.1.0",
    "license": "AGPL-3",
    "author": "Noviat",
    "website": "https://www.noviat.com",
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
    "images": ["static/description/cover.png"],
}
