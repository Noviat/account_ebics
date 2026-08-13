# Copyright 2022 Noviat.
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

{
    "name": "EBICS automated file import",
    "version": "19.0.1.0.1",
    "license": "LGPL-3",
    "author": "Noviat",
    "website": "https://www.noviat.com/",
    "category": "Accounting & Finance",
    "summary": "Download and process your EBICS files automatically, on a schedule",
    "depends": ["account_ebics"],
    "data": [
        "security/ir.model.access.csv",
        "data/ir_cron_data.xml",
        "views/ebics_batch_log_views.xml",
        "views/menu.xml",
    ],
    "images": ["static/description/cover.png"],
}
