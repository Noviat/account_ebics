# Copyright 2022 Noviat.
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

{
    "name": "EBICS Files batch import",
    "version": "19.0.1.0.0",
    "license": "LGPL-3",
    "author": "Noviat",
    "website": "https://www.noviat.com/",
    "category": "Accounting & Finance",
    "summary": "EBICS Files automated import and processing",
    "depends": ["account_ebics"],
    "data": [
        "security/ir.model.access.csv",
        "data/ir_cron_data.xml",
        "views/ebics_batch_log_views.xml",
        "views/menu.xml",
    ],
    "images": ["static/description/cover.png"],
}
