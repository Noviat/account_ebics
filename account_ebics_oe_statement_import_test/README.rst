=========================================
EBICS - Enterprise Statement Import Tests
=========================================

**Test-only module. Do not install it on a production database.**

It carries no code and no data. It exists so that continuous integration
installs the Odoo Enterprise CAMT parser (``account_bank_statement_import_camt``)
next to ``account_ebics`` and runs the statement import tests through the
Enterprise import. It is excluded from the Community test job.

Credits
=======

Developed and maintained by `Noviat <https://www.noviat.com>`_.
