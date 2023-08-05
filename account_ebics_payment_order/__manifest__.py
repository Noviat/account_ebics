# Copyright 2009-2023 Noviat.
# License LGPL-3 or later (http://www.gnu.org/licenses/lgpl).

{
    "name": "Upload Payment Order via EBICS",
    "version": "16.0.1.0.0",
    "license": "LGPL-3",
    "author": "Noviat",
    "website": "https://www.noviat.com",
    "category": "Accounting & Finance",
    "depends": ["account_ebics", "account_payment_order"],
    "data": [
        "views/account_payment_order_views.xml",
    ],
    "images": ["static/description/cover.png"],
    "installable": True,
}
