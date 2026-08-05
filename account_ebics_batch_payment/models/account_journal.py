# Copyright 2026 Noviat.
# License LGPL-3 or later (http://www.gnu.org/licenses/lgpl).

from odoo import fields, models


class AccountJournal(models.Model):
    _inherit = "account.journal"

    ebics_file_format_ids = fields.Many2many(
        comodel_name="ebics.file.format",
        related="ebics_config_id.ebics_file_format_ids",
    )
