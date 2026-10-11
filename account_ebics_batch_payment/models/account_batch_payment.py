# Copyright 2020 Noviat.
# License LGPL-3 or later (http://www.gnu.org/licenses/lgpl).

from odoo import api, fields, models
from odoo.exceptions import UserError


class AccountBatchPayment(models.Model):
    _inherit = "account.batch.payment"

    ebics_config_id = fields.Many2one(
        comodel_name="ebics.config",
        related="journal_id.ebics_config_id",
    )
    ebics_file_id = fields.Many2one(
        comodel_name="ebics.file",
        string="EBICS Upload File",
        readonly=True,
    )
    ebics_pain_state = fields.Selection(
        related="ebics_file_id.pain_state",
        string="EBICS Upload Status",
    )
    ebics_order_number = fields.Char(
        related="ebics_file_id.ebics_order_number",
        string="EBICS OrderID",
    )
    hide_ebics_upload = fields.Boolean(
        compute="_compute_hide_ebics_upload", default=True
    )

    @api.depends(
        "journal_id.ebics_config_id",
        "file_generation_enabled",
        "state",
        "ebics_file_id.pain_state",
    )
    def _compute_hide_ebics_upload(self):
        for rec in self:
            rec.hide_ebics_upload = (
                self.env.neutralized
                or not rec.journal_id.ebics_config_id
                or not rec.file_generation_enabled
                or rec.state != "sent"
                or rec.ebics_pain_state == "uploaded"
            )

    def export_batch_payment(self):
        self.filtered("ebics_file_id").write({"ebics_file_id": False})
        return super().export_batch_payment()

    def ebics_upload(self):
        self.ensure_one()
        ctx = self.env.context.copy()

        origin = self.env._("Batch Payment") + ": " + self.name
        if not self.journal_id.ebics_config_id:
            raise UserError(
                self.env._(
                    "No active EBICS configuration available for the selected bank."
                )
            )
        ctx.update(
            {
                "default_ebics_config_id": self.journal_id.ebics_config_id.id,
                "default_upload_data": self.export_file,
                "default_upload_fname": self.export_filename,
                "origin": origin,
                "model": self._name,
                "id": self.id,
            }
        )

        ebics_xfer = (
            self.env["ebics.xfer"]
            .with_company(self.journal_id.company_id)
            .with_context(**ctx)
            .create({})
        )
        ebics_xfer._onchange_ebics_config_id()
        ebics_xfer._onchange_upload_data()
        if not ebics_xfer.format_id and self.payment_method_id.ebics_file_format_id:
            ebics_xfer.format_id = self.payment_method_id.ebics_file_format_id
        view = self.env.ref("account_ebics.ebics_xfer_view_form_upload")
        act = {
            "name": self.env._("EBICS Upload"),
            "view_mode": "form",
            "res_model": "ebics.xfer",
            "view_id": view.id,
            "res_id": ebics_xfer.id,
            "type": "ir.actions.act_window",
            "target": "new",
            "context": ctx,
        }
        return act
