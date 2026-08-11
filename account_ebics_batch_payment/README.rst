.. image:: https://img.shields.io/badge/license-LGPL--3-blue.png
   :target: https://www.gnu.org/licenses/lgpl
   :alt: License: LGPL-3

===============================
EBICS upload for batch payments
===============================

**Send a payment batch to the bank from Odoo, without touching a file.**

This module allows to upload an Odoo Enterprise Batch Payment to the bank via the EBICS
protocol. You validate the batch, Odoo generates the payment file in the format the bank
expects and submits it. Nothing is exported to a folder and nothing is uploaded to a
portal, which also means nothing can be altered on the way.

Installation
============

This module depends upon the following modules:

- account_ebics (cf. https://github.com/Noviat/account_ebics)
- account_ebics_oe (cf. https://github.com/Noviat/account_ebics)
- account_batch_payment (Odoo Enterprise)

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
