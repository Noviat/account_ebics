# Copyright 2026 Noviat.
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo.upgrade import util


def migrate(cr, version):
    """
    Remove account_ebics_batch module record and its meta-entries since this
    module is now merged into the base account_ebics module.
    """
    util.remove_module(cr, "account_ebics_batch")
