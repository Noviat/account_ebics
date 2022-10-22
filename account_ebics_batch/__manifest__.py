
{
    "name": "EBICS Files batch import",
    "version": "12.0.1.0.0",
    "license": "AGPL-3",
    "author": "Noviat",
    "website": "http://www.noviat.com",
    "category": "Accounting & Finance",
    "summary": "EBICS Files automated import and processing",
    "depends": ["account_ebics"],
    "data": [
        "security/ir.model.access.csv",
        "data/ir_cron_data.xml",
        "views/ebics_batch_log_views.xml",
        "views/menu.xml",
    ],
    "installable": True,
}
