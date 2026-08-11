.. image:: https://img.shields.io/badge/license-LGPL--3-blue.png
   :target: https://www.gnu.org/licenses/lgpl
   :alt: License: LGPL-3

======================
EBICS banking protocol
======================

**Exchange files directly with your banks from Odoo, with no portal and nobody logging in.**

EBICS, the Electronic Banking Internet Communication Standard, is the channel European
banks open to companies that want their software to talk to the bank. Bank statements are
downloaded on a schedule and payment files are uploaded from Odoo, authenticated by your
own cryptographic keys instead of a login page.

This module implements that protocol in Odoo. It has been developed and maintained by
Noviat since 2015, on every major version of Odoo from 8.0 onwards.

If you are still working out whether EBICS is the right channel for you, we explain it
without the jargon, with screen recordings of the flow in Odoo, on
`noviat.com/ebics <https://www.noviat.com/ebics>`_.

|

.. image:: https://raw.githubusercontent.com/Noviat/account_ebics/19.0/account_ebics/static/description/ebics_flow.png
   :alt: Statements come down as camt or MT940 files, payment files go up as pain.001 or pain.008, and your keys stay on your own server
   :width: 100%

|

What you get
============

- **Statements that arrive on their own.** A scheduled task collects the files your bank
  publishes, for every account, and processes them into bank statements.
- **Payments that leave the same way.** A payment batch or a payment order is uploaded to
  the bank in the format the bank expects, without exporting a file and re-uploading it
  somewhere else.
- **A test mode.** Uploads can be validated against the bank before anything counts as a
  real payment.
- **A trace of every exchange.** Each download and each upload is a record, with the file
  it carried, the moment it happened and the user behind it.

Both **EBICS 2.5** and **EBICS 3.0** are supported.

|

Which banks
===========

Any bank that publishes an EBICS access point can be connected. The standard is owned by
EBICS SC, a company held by the German, French, Swiss and Austrian banking bodies
(DK, CFONB, SIX and PSA), and it is the ordinary corporate channel in those countries.

To check a specific bank before you start, joonis publishes a public directory at
`joonis.de/en/fintech/banks <https://www.joonis.de/en/fintech/banks/>`_.

|

What it costs
=============

**This module is free software**, published under LGPL-3. There is no licence fee, no
subscription and no per-connection charge from Noviat.

It does however rely on the `fintech <https://pypi.python.org/pypi/fintech>`_ library from
joonis, and that library requires a **commercial licence for production use**: as soon as
you upload SEPA files with more than five transactions, retrieve statements older than the
last three days, or use the distributed signature. The licence is contracted directly with
joonis, not with Noviat.

At the time of writing, joonis charges a one-off setup fee plus a monthly fee per EBICS
user id. Current pricing is published on
`joonis.de <https://www.joonis.de/en/fintech/prices/>`_.

|

Requirements
============

The module depends upon

- https://pypi.python.org/pypi/fintech
- https://pypi.python.org/pypi/cryptography

Because the connection needs a Python library and your key files on the server, it runs on
**Odoo.sh** or on an **on-premise** installation.

Remark:

The EBICS 'Test Mode' for uploading orders requires fintech 4.3.4 or higher for EBICS 2.x
and fintech 7.2.7 or higher for EBICS 3.0.

SWIFT 3SKey support requires fintech 6.4 or higher.

|

Fintech license
---------------

If you have a valid fintech.ebics license, you should add the following
licensing parameters to the [options] section of the odoo server configuration file:


- fintech_register_name

The name of the licensee.

- fintech_register_keycode

The keycode of the licensed version.

|
| Example:
|

::

 ; fintech
 fintech_register_name = MyCompany
 fintech_register_keycode = AB1CD-E2FG-3H-IJ4K-5L

|

Companion modules
=================

|

- account_ebics_oe

  Required if you are running Odoo Enterprise

  Cf. https://github.com/Noviat/account_ebics

|

- account_ebics_batch

  This module adds a cron job for the automated import of EBICS files.

  Cf. https://github.com/Noviat/account_ebics

|

- account_ebics_batch_payment

  Recommended if you are using the Odoo Enterprise account_batch_payment module

  Cf. https://github.com/Noviat/account_ebics

|

- account_ebics_payment_order

  Required if you are using the OCA account_payment_order module.

  Cf. https://github.com/OCA/bank-payment

|

- account_usability

  Recommended if you have multiple financial journals.
  This module adds a number of accounting menu entries such as bank statement list view
  which allows to see all statements downloaded via the ir.cron automated EBICS download.

  Cf. https://github.com/OCA/account-financial-tools

|

- account_ebics_oca_statement_import

  Required if you are using the OCA Bank Statement import modules.

  https://github.com/OCA/bank-statement-import

|

- account_statement_import_fr_cfonb

  Required to handle french CFONB files.

  Cf. https://github.com/OCA/l10n_france

|

- account_statement_import_camt

  Required to handle camt.052 and camt.054 files.

  Cf. https://github.com/OCA/bank-statement-import

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

For File Formats of type 'Downloads' you can also specify a 'Download Process Method'.

This is the method that will be executed when hitting the 'Process' button on the downloaded file.

The following methods are currently available:

- cfonb120
- camt.053
- camt.052
- camt.054

All these methods require complimentary modules to be installed (cf. Companion modules supra).

You'll get an error message when the required module is not installed on your Odoo instance.

|

Go to **Accounting > Configuration > Miscellaneous > EBICS > EBICS Configuration**

Configure your EBICS configuration according to the contract with your bank.

|

.. image:: https://raw.githubusercontent.com/Noviat/account_ebics/19.0/account_ebics/static/description/ebics_download.png
   :alt: A downloaded camt.053 statement file in Odoo, before processing
   :width: 100%

|

Usage
=====

Go to **Accounting > Bank and Cash > EBICS Processing**

Downloaded files are listed there and can be processed into bank statements. Uploads are
launched from the payment batch or payment order, and the file, its format and the order
type are taken from the EBICS configuration rather than chosen by the user.

|

.. image:: https://raw.githubusercontent.com/Noviat/account_ebics/19.0/account_ebics/static/description/ebics_upload.png
   :alt: Uploading a pain.001 SEPA credit transfer file over EBICS 3.0, with the test mode option
   :width: 100%

|

Diagnostics
===========

Add the following to your Odoo config file in order to diagnose
issues with the EBICS connection with your bank:

log_handler = fintech.ebics:DEBUG

|

EBICS Return Codes
------------------

During the processing of your EBICS upload/download, your bank may return an Error Code, e.g.

EBICS Functional Error:
EBICS_NO_DOWNLOAD_DATA_AVAILABLE (code: 90005)

A detailed explanation of the codes can be found on http://www.ebics.org.
You can also find this information in the doc folder of this module (file EBICS_Annex1_ReturnCodes).

|

Electronic Distributed Signature (EDS)
--------------------------------------

This is supported via external signing apps, e.g. BankingVEU:

- https://play.google.com/store/apps/details?id=subsembly.bankingveu
- https://apps.apple.com/de/app/bankingveu/id1578694190

|

Roadmap
=======

- The end user is currently not able to change his passphrases (only the users with 'EBICS Manager' rights can do so).
- Add support to import externally generated keys & certificates (currently only 3SKey signature certificate).
- Add support for SWIFT 3SKey signing javascript lib (SConnect, cf https://www2.swift.com/3skey/help/sconnect.html).

Issues and pull requests are welcome on https://github.com/Noviat/account_ebics.

|

Credits
=======

This module is developed and maintained by `Noviat <https://www.noviat.com>`_, an Odoo
partner in Belgium specialised in accounting and finance since 2009.

We implement it, we configure the connection with your banks and we support you through
the first cycles. If you want help getting a bank online, tell us which banks you use on
`noviat.com/ebics <https://www.noviat.com/ebics>`_ and we will tell you what it takes.
