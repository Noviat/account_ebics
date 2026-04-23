# Copyright 2026 Noviat.
# License LGPL-3 or later (https://www.gnu.org/licenses/lgpl).

from odoo import api, fields, models


class AccountJournal(models.Model):
    _inherit = "account.journal"

    ebics_config_ids = fields.Many2many(
        comodel_name="ebics.config",
        relation="account_journal_ebics_config_rel",
        readonly=True,
        string="Ebics Configs",
    )
    ebics_config_id = fields.Many2one(
        comodel_name="ebics.config",
        compute="_compute_ebics_config_id",
        compute_sudo=True,
        string="Ebics Config",
    )

    @api.depends("ebics_config_ids")
    def _compute_ebics_config_id(self):
        for rec in self:
            rec.ebics_config_id = rec.ebics_config_ids.filtered(
                lambda r: r.state == "confirm"
            )[:1]
