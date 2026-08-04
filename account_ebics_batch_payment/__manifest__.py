# Copyright 2020 Noviat.
# License LGPL-3 or later (http://www.gnu.org/licenses/lgpl).

{
    "name": "Upload Batch Payment via EBICS",
    "version": "18.0.1.2.0",
    "license": "LGPL-3",
    "author": "Noviat",
    "website": "https://www.noviat.com/",
    "category": "Accounting & Finance",
    "depends": ["account_ebics", "account_batch_payment"],
    "data": [
        "views/account_journal_views.xml",
        "views/account_batch_payment_views.xml",
    ],
    "installable": True,
    "images": ["static/description/cover.png"],
}
