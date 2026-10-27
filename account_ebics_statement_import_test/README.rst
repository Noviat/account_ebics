==============================
EBICS - Statement Import Tests
==============================

**Test-only module. Do not install it on a production database.**

It carries no code and no data. It exists so that continuous integration
installs the OCA statement parsers (``account_statement_import_camt`` and
``account_statement_import_fr_cfonb``) next to ``account_ebics`` and runs the
end-to-end statement import tests: EBICS download, split per account, bank
statement creation.

Credits
=======

Developed and maintained by `Noviat <https://www.noviat.com>`_.
