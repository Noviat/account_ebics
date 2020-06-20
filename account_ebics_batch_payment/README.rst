.. image:: https://img.shields.io/badge/licence-LGPL--3-blue.svg
   :target: https://www.gnu.org/licenses/lpgl
   :alt: License: AGPL-3

==============================
Upload Batch Payment via EBICS
==============================

This module allows to upload a Batch Payment to the bank via the EBICS protocol.

Installation
============

This module depends upon the following modules:

- account_ebics (cf. https://github.com/Noviat/account_ebics)
- account_ebics_oe (cf. https://github.com/Noviat/account_ebics)
- account_batch_payment (Odoo Enterprise)

Usage
=====

Create your Batch Payment and generate the bank file.
Upload the generated file via the 'EBICS Upload' button on the batch payment.

Known issues / Roadmap
======================

 * Add support for multiple EBICS connections.
