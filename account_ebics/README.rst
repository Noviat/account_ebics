.. image:: https://img.shields.io/badge/license-AGPL--3-blue.png
   :target: https://www.gnu.org/licenses/agpl
   :alt: License: AGPL-3

======================
EBICS banking protocol
======================

Implementation of the  EBICS banking protocol.

This module facilitates the exchange of files with banks via the EBICS protocol.

Installation
============

The module depends upon

- https://pypi.python.org/pypi/fintech
- https://pypi.python.org/pypi/cryptography

Remark:

The EBICS 'Test Mode' for uploading orders requires Fintech 4.3.4 or higher.

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

Configuration
=============

Go to **Settings > Users**

Add the users that are authorised to maintain the EBICS configuration to the 'EBICS Manager' Group.

Go to **Accounting > Configuration > Miscellaneous > EBICS > EBICS Configuration**

Configure your EBICS configuration according to the contract with your bank.

Usage
=====

Go to **Accounting > Bank and Cash > EBICS Processing**

EBICS Return Codes
------------------

During the processing of your EBICS upload/download, your bank may return an Error Code, e.g.

EBICS Functional Error:
EBICS_NO_DOWNLOAD_DATA_AVAILABLE (code: 90005)

A detailled explanation of the codes can be found on http://www.ebics.org.
You can also find this information in the doc folder of this module (file EBICS_Annex1_ReturnCodes).
