.. image:: https://img.shields.io/badge/licence-LGPL--3-blue.svg
   :target: https://www.gnu.org/licenses/lpgl
   :alt: License: AGPL-3

==============================
Upload Payment Order via EBICS
==============================

This module allows to upload a Payment Order to the bank via the EBICS protocol.

Installation
============

This module depends upon the following modules (cf. apps.odoo.com):

- account_ebics
- account_payment_order

Usage
=====

Create your Payment Order and generate the bank file.
Upload the generated file via the 'EBICS Upload' button on the payment order.

Known issues / Roadmap
======================

 * Add support for multiple EBICS connections.
