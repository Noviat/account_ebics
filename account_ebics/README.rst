.. image:: https://img.shields.io/badge/license-LGPL--3-blue.png
   :target: https://www.gnu.org/licenses/lpgl
   :alt: License: LGPL-3

======================
EBICS banking protocol
======================

Implementation of the  EBICS banking protocol.

This module facilitates the exchange of files with banks via the EBICS protocol.

|

Installation
============

The module depends upon

- https://pypi.python.org/pypi/fintech
- https://pypi.python.org/pypi/cryptography

Remark:

The EBICS 'Test Mode' for uploading orders requires Fintech 4.3.4 or higher.

SWIFT 3SKey support requires Fintech 6.4 or higher.
|

We also recommend to consider the installation of the following modules:

|

- account_ebics_oe

  Required if you are running Odoo Enterprise

|

- account_ebics_batch_payment

  Recommended if you are using the Odoo Enterprise account_batch_payment module

|

- account_ebics_payment_order

  Recommended if you are using the OCA account_payment_order module.

  Cf. https://github.com/OCA/bank-payment

|

- account_bank_statement_import_fr_cfonb

  Required to handle french CFONB files.

  Cf. https://github.com/OCA/l10n_fr

|

- account_bank_statement_import_camt_oca

  Required to handle camt.052 and camt.054 files.

  Cf. https://github.com/OCA/bank_statement_import

|

- account_bank_statement_import_helper

  Required if you are processing bank statements with local bank account numbers (e.g. french CFONB files).

  The import helper will match the local bank account number with the IBAN number specified on the Odoo Financial journal.

  Cf. https://github.com/noviat-apps

|

Fintech license
---------------

If you have a valid Fintech.ebics license, you should add the following
licensing parameters to the odoo server configuration file:


- fintech_register_name

The name of the licensee.

- fintech_register_keycode

The keycode of the licensed version.

- fintech_register_users

The licensed EBICS user ids. It must be a string or a list of user ids.

You should NOT specify this parameter if your license is subsciption
based (with monthly recurring billing).

|
| Example:
|

::

 ; fintech
 fintech_register_name = MyCompany
 fintech_register_keycode = AB1CD-E2FG-3H-IJ4K-5L
 fintech_register_users = USER1, USER2

|

Configuration
=============

Go to **Settings > Users**

Add the users that are authorised to maintain the EBICS configuration to the 'EBICS Manager' Group.

|

Go to **Accounting > Configuration > Miscellaneous > EBICS > EBICS File Formats**

Check if the EBICS File formats that you want to process in Odoo are defined.

Most commonly used formats for which support is available in Odoo should be there already.

Please open an issue on https://github.com/Noviat/account_ebics to report missing EBICS File Formats.

For File Formats of type 'Downloads' you can also specifiy a 'Download Process Method'.

This is the method that will be executed when hitting the 'Process' button on the downloaded file.

The following methods are currently available:

- cfonb120
- camt.053
- camt.052
- camt.054

All these methods require complimentary modules to be installed (cf. Installation section supra).

You'll get an error message when the required module is not installed on your Odoo instance.

|

Go to **Accounting > Configuration > Miscellaneous > EBICS > EBICS Configuration**

Configure your EBICS configuration according to the contract with your bank.

|

Usage
=====

Go to **Accounting > Bank and Cash > EBICS Processing**

|

EBICS Return Codes
------------------

During the processing of your EBICS upload/download, your bank may return an Error Code, e.g.

EBICS Functional Error:
EBICS_NO_DOWNLOAD_DATA_AVAILABLE (code: 90005)

A detailled explanation of the codes can be found on http://www.ebics.org.
You can also find this information in the doc folder of this module (file EBICS_Annex1_ReturnCodes).

|

Known Issues / Roadmap
======================

- add support for EBICS 3.0
- add support to import externally generated keys & certificates (currently only 3SKey signature certificate)
