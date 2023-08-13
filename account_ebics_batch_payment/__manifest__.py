# Copyright 2009-2022 Noviat.
# License LGPL-3 or later (http://www.gnu.org/licenses/lpgl).

{
    "name": "Upload Batch Payment via EBICS",
    "version": "15.0.1.0.0",
    "license": "LGPL-3",
    "author": "Noviat",
    "website": "https://www.noviat.com/",
    "category": "Accounting & Finance",
    "depends": ["account_ebics", "account_batch_payment"],
    "data": ["views/account_batch_payment_views.xml"],
    "installable": True,
    "images": ["static/description/cover.png"],
}
