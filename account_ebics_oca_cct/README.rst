.. image:: https://img.shields.io/badge/licence-AGPL--3-blue.svg
   :target: https://www.gnu.org/licenses/agpl
   :alt: License: AGPL-3

==============================
Upload Payment Order via EBICS
==============================

This module allows to upload a CCT Payment Order to the bank via the EBICS protocol.

Installation
============

This module depends upon the following modules (cf. apps.odoo.com):

- account_ebics
- account_banking_sepa_credit_transfer

Usage
=====

Create your Payment Order and generate the ISO 20022 Credit Transfer File.
The wizard that allows to download this XML file now has an extra button called 'EBICS Upload'
in order to send this file directly to your bank.
