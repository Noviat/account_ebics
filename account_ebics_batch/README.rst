.. image:: https://img.shields.io/badge/license-AGPL--3-blue.png
   :target: https://www.gnu.org/licenses/agpl
   :alt: License: AGPL-3

============================================
Module to enable batch import of EBICS files
============================================

This module adds a cron job for the automated import of EBICS files.

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

