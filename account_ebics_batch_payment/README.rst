========================================
EBICS - Batch Payments (Odoo Enterprise)
========================================

**Send a payment batch to the bank from Odoo, without touching a file.**

This module lets you upload an Odoo Enterprise batch payment to the bank over EBICS. You
validate the batch, Odoo generates the payment file in the format the bank expects and
submits it. Nothing is exported to a folder and nothing is uploaded to a portal, which also
means nothing can be altered on the way.

.. image:: https://raw.githubusercontent.com/Noviat/account_ebics/19.0/account_ebics_batch_payment/static/description/ebics_upload.png
   :alt: Uploading a payment file over EBICS, with the test mode option
   :width: 100%

Installation
============

This module depends on:

- ``account_ebics`` (https://github.com/Noviat/account_ebics);
- ``account_batch_payment`` (Odoo Enterprise).

Configuration
=============

On the bank journal, in the incoming and outgoing payment methods, show the optional
**EBICS File Format** column and set the format of each payment method, for example
pain.001 for SEPA credit transfers and pain.008 for direct debits. The formats offered are
those of the journal's confirmed EBICS connection.

Usage
=====

Validate the batch payment, then click **EBICS Upload**.

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
