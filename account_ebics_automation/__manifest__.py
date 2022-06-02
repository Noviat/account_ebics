# © 2022 initOS GmbH
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "Automated EBICS",
    "version": "14.0.1.0.0",
    "category": "Hidden",
    "author": "initOS GmbH",
    "website": "https://www.initos.com",
    "license": "AGPL-3",
    "summary": "Automated download via EBICS for all configurations",
    "depends": [
        "account_ebics",
    ],
    "data": [
        "data/ir_cron.xml",
    ],
    "installable": True,
}
