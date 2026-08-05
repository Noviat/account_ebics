# Copyright 2026 Noviat.
# License LGPL-3 or later (http://www.gnu.org/licenses/lgpl).

from odoo import api, fields, models


class AccountJournal(models.Model):
    _inherit = "account.journal"

    ebics_file_format_ids = fields.Many2many(
        comodel_name="ebics.file.format",
        compute="_compute_ebics_file_format_ids",
    )

    @api.depends("ebics_config_ids.ebics_file_format_ids", "ebics_config_ids.state")
    def _compute_ebics_file_format_ids(self):
        for rec in self:
            config = rec.ebics_config_ids.filtered(lambda r: r.state == "confirm")[:1]
            rec.ebics_file_format_ids = config.ebics_file_format_ids
