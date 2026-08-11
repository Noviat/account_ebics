# Copyright 2019 Noviat.
# License LGPL-3 or later (https://www.gnu.org/licenses/lgpl).

{
    "name": "EBICS for Odoo Enterprise",
    "summary": "Place the EBICS menus in the Odoo Enterprise accounting application",
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
