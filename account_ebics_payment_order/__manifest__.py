# Copyright 2009-2023 Noviat.
# License AGPL-3 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "Upload Payment Order via EBICS",
    "version": "16.0.1.0.0",
    "license": "AGPL-3",
    "author": "Noviat",
    "website": "https://www.noviat.com",
    "category": "Accounting & Finance",
    "depends": ["account_ebics", "account_payment_order"],
    "data": [
        "views/account_payment_order_views.xml",
    ],
    # installable False until OCA payment order becomes
    # available for 16.0
    "images": ["static/description/cover.png"],
    "installable": False,
}
