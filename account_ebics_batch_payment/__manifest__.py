# Copyright 2020 Noviat.
# License LGPL-3 or later (http://www.gnu.org/licenses/lgpl).

{
    "name": "EBICS - Batch Payments (Odoo Enterprise)",
    "summary": "Send an Odoo Enterprise batch payment to the bank over EBICS",
    "version": "18.0.1.3.0",
    "license": "LGPL-3",
    "author": "Noviat",
    "website": "https://www.noviat.com/",
    "category": "Accounting & Finance",
    "depends": ["account_ebics", "account_batch_payment"],
    "data": [
        "views/account_journal_views.xml",
        "views/account_batch_payment_views.xml",
    ],
    "images": ["static/description/banner.png"],
}
