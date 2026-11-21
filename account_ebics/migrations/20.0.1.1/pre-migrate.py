# Copyright 2026 Noviat.
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from openupgradelib import openupgrade


def migrate(cr, version):
    openupgrade.logged_query(
        cr,
        """
        UPDATE ir_model_data SET module = 'account_ebics'
        WHERE module = 'account_ebics_batch'
        AND name NOT IN (
            SELECT name FROM ir_model_data WHERE module = 'account_ebics'
        )
        """,
    )
    openupgrade.logged_query(
        cr,
        "UPDATE ir_module_module_dependency SET name = 'account_ebics'"
        " WHERE name = 'account_ebics_batch'",
    )
