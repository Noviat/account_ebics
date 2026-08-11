# Copyright 2020 Noviat.
# License LGPL-3 or later (https://www.gnu.org/licenses/lgpl).

{
    "name": "EBICS upload for batch payments",
    "summary": "Send an Odoo Enterprise batch payment to the bank over EBICS",
    "version": "19.0.1.2.0",
    "license": "LGPL-3",
    "author": "Noviat",
    "website": "https://www.noviat.com/",
    "category": "Accounting & Finance",
    "depends": ["account_ebics", "account_batch_payment"],
    "data": [
        "views/account_journal_views.xml",
        "views/account_batch_payment_views.xml",
    ],
    "images": ["static/description/cover.png"],
}
