# Copyright 2009-2024 Noviat.
# License LGPL-3 or later (http://www.gnu.org/licenses/lgpl).

{
    "name": "EBICS - Batch Payments (Odoo Enterprise)",
    "summary": "Send an Odoo Enterprise batch payment to the bank over EBICS",
    "version": "16.0.1.0.2",
    "license": "LGPL-3",
    "author": "Noviat",
    "website": "https://www.noviat.com/",
    "category": "Accounting & Finance",
    "depends": ["account_ebics", "account_batch_payment"],
    "data": ["views/account_batch_payment_views.xml"],
    "installable": True,
    "images": ["static/description/banner.png"],
}
