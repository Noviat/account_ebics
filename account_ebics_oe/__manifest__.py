# Copyright 2019 Noviat.
# License LGPL-3 or later (https://www.gnu.org/licenses/lgpl).

{
    "name": "account_ebics on Odoo Enterprise",
    "summary": "Deploy account_ebics module on Odoo Enterprise",
    "version": "19.0.1.0.0",
    "author": "Noviat",
    "website": "https://www.noviat.com/",
    "category": "Hidden",
    "license": "LGPL-3",
    "depends": [
        "account_ebics",
        "accountant",
    ],
    "data": ["views/account_ebics_menu.xml"],
    "auto_install": True,
    "images": ["static/description/cover.png"],
}
