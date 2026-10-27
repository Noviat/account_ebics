# Copyright 2026 Noviat.
# License LGPL-3 or later (https://www.gnu.org/licenses/lgpl).

{
    "name": "EBICS - Statement Import Tests",
    "summary": "Test-only module, do not install: runs the EBICS statement "
    "import tests against the OCA CAMT and CFONB parsers",
    "version": "18.0.1.0.0",
    "license": "LGPL-3",
    "author": "Noviat",
    "website": "https://www.noviat.com/",
    "category": "Hidden",
    "depends": [
        "account_ebics_oca_statement_import",
        "account_statement_import_camt",
        "account_statement_import_fr_cfonb",
    ],
}
