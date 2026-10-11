============================
EBICS - Payment Orders (OCA)
============================

**Send an OCA payment order to the bank from Odoo, without touching a file.**

This module lets you upload a payment order of the OCA ``account_payment_order`` module to
the bank over EBICS.

.. image:: https://raw.githubusercontent.com/Noviat/account_ebics/17.0/account_ebics_payment_order/static/description/ebics_upload.png
   :alt: Uploading a payment file over EBICS, with the test mode option
   :width: 100%

Installation
============

This module depends on:

- ``account_ebics`` (https://github.com/Noviat/account_ebics);
- ``account_payment_order`` (https://github.com/OCA/bank-payment).

Configuration
=============

Set the **EBICS File Format** on your payment modes.

Usage
=====

Create the payment order and generate the bank file, then upload it with the **EBICS
Upload** button of the payment order.

Part of the EBICS suite
=======================

This module extends **EBICS Banking Protocol** (``account_ebics``), the EBICS implementation
for Odoo developed and maintained by Noviat. Install it first:
https://github.com/Noviat/account_ebics

What EBICS is and what it changes, in plain language, with screen recordings of the flow:
https://www.noviat.com/ebics

Credits
=======

Developed and maintained by `Noviat <https://www.noviat.com>`_, Odoo integrator in Belgium,
specialised in accounting and finance since 2009. We configure the connection with your banks
and support you through the first cycles.
