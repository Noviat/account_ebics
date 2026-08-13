.. image:: https://img.shields.io/badge/license-LGPL--3-blue.png
   :target: https://www.gnu.org/licenses/lgpl
   :alt: License: LGPL-3

===========================
EBICS automated file import
===========================

**Your statements arrive without anyone asking for them.**

This module adds a cron job that downloads and processes EBICS files automatically, on all
confirmed EBICS connections. This is what turns EBICS from a manual download into
something your morning no longer depends on.

|

A Log is created during the import in order to document import errors.
If errors have been detected, the Batch Import Log state is set to 'error'.

When all EBICS Files have been imported correctly, the Batch Import Log state is set to 'done'.

|

The user can reprocess the imported EBICS files in status 'draft' via the Log object 'REPROCESS' button until all errors have been cleared.

As an alternative, the user can force the Batch Import Log state to 'done'
(e.g. when the errors have been circumvented via manual encoding or the reprocessing of a single EBICS file).

|

Configuration
=============

Adapt the 'EBICS Batch Import' ir.cron job created during the module installation.

The cron job calls the following python method:

|

.. code-block:: python

  _batch_import()


The EBICS download will be performed on all confirmed EBICS connections.

You can limit the automated operation to a subset of your EBICS connections via the ebics_config_ids parameter, e.g.

|

.. code-block:: python

  _batch_import(ebics_config_ids=[1,3])


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
