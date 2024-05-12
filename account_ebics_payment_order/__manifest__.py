# Copyright 2009-2024 Noviat.
# License LGPL-3 or later (http://www.gnu.org/licenses/lpgl).

{
    "name": "Upload Payment Order via EBICS",
    "version": "15.0.1.1.1",
    "license": "LGPL-3",
    "author": "Noviat",
    "website": "https://www.noviat.com/",
    "category": "Accounting & Finance",
    "depends": ["account_ebics", "account_payment_order"],
    "data": [
        "views/account_payment_order_views.xml",
        "views/account_payment_mode_views.xml",
    ],
    "installable": True,
    "images": ["static/description/cover.png"],
}
