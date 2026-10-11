===================================
EBICS - Bank Statement Import (OCA)
===================================

**Each statement in the right journal, even when one file carries many.**

This module connects the files downloaded over EBICS to the OCA bank statement import. When a
file holds the statements of several accounts or companies, each statement is created in the
right bank journal, including when the bank appends a currency code to the account number
(for example ``BE..EUR``). A file without transactions, or a statement already imported, gives
a warning on the EBICS file instead of a blocking error.

.. image:: https://raw.githubusercontent.com/Noviat/account_ebics/16.0/account_ebics_oca_statement_import/static/description/ebics_download.png
   :alt: A downloaded camt.053 statement file in Odoo, ready to be processed
   :width: 100%

Installation
============

This module depends on:

- ``account_ebics`` (https://github.com/Noviat/account_ebics);
- ``account_statement_import_file`` (https://github.com/OCA/bank-statement-import).

It is installed automatically when both are installed, which is the case as soon as an OCA
statement import module such as ``account_statement_import_camt`` is installed.

Usage
=====

There is nothing to configure. Process a downloaded EBICS file, by hand with the **Process**
button or with the scheduled import: the bank statements are created in their journals. The
journal matching also applies to statements imported by hand with the OCA import.

