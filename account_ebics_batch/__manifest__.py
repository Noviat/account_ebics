# Copyright 2009-2025 Noviat.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "EBICS - Scheduled File Import",
    "version": "18.0.1.0.2",
    "license": "AGPL-3",
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
    "images": ["static/description/banner.png"],
}
