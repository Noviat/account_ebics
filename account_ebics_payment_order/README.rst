.. image:: https://img.shields.io/badge/license-LGPL--3-blue.png
   :target: https://www.gnu.org/licenses/lgpl
   :alt: License: LGPL-3

===============================
EBICS upload for payment orders
===============================

**Send an OCA payment order to the bank from Odoo, without touching a file.**

This module allows to upload a payment order created with the OCA account_payment_order
module to the bank via the EBICS protocol.

Installation
============

This module depends upon the following modules:

- account_ebics (cf. https://github.com/Noviat/account_ebics)
- account_payment_order (cf. https://github.com/OCA/bank-payment)

Configuration
=============

Set the EBICS File Format on your Payment Modes.

Usage
=====

Create your Payment Order and generate the bank file.
Upload the generated file via the 'EBICS Upload' button on the payment order.

|

Part of the EBICS suite
=======================

This module extends **account_ebics**, the EBICS banking protocol implementation for Odoo,
developed and maintained by `Noviat <https://www.noviat.com>`_ since 2015.

Start with account_ebics if you have not installed it yet:
https://github.com/Noviat/account_ebics

What EBICS is and what it changes, in plain language, with screen recordings of the flow:
`noviat.com/ebics <https://www.noviat.com/ebics>`_.

|

Credits
=======

Developed and maintained by `Noviat <https://www.noviat.com>`_, an Odoo partner in Belgium
specialised in accounting and finance since 2009. We configure the connection with your
banks and support you through the first cycles.
