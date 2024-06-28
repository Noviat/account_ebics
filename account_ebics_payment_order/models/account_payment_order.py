# Copyright 2009-2024 Noviat.
# License LGPL-3 or later (http://www.gnu.org/licenses/lgpl).

from odoo import _, models
from odoo.exceptions import UserError


class AccountPaymentOrder(models.Model):
    _inherit = "account.payment.order"

    def ebics_upload(self):
        self.ensure_one()
        ctx = self.env.context.copy()
        ebics_format_id = self.payment_mode_id.ebics_format_id
        if not ebics_format_id:
            raise UserError(
                _("Missing EBICS File Format setting on your Payment Mode.")
            )
        ctx.update(
            {
                "active_model": self._name,
                "default_format_id": ebics_format_id.id,
            }
        )
        attach = self.env["ir.attachment"].search(
            [("res_model", "=", self._name), ("res_id", "=", self.id)]
        )
        if not attach:
            raise UserError(
                _(
                    "This payment order doesn't contains attachements."
                    "\nPlease generate first the Payment Order file first."
                )
            )
        elif len(attach) > 1:
            raise UserError(
                _(
                    "This payment order contains multiple attachments."
                    "\nPlease remove the obsolete attachments or upload "
                    "the payment order file via the "
                    "EBICS Processing > EBICS Upload menu"
                )
            )
        else:
            origin = _("Payment Order") + ": " + self.name
            ebics_config = self.env["ebics.config"].search(
                [
                    ("journal_ids", "=", self.journal_id.id),
                    ("state", "=", "confirm"),
                ]
            )
            if not ebics_config:
                raise UserError(
                    _(
                        "No active EBICS configuration available "
                        "for the selected bank."
                    )
                )
            if len(ebics_config) == 1:
                ctx["default_ebics_config_id"] = ebics_config.id
            ctx.update(
                {
                    "default_upload_data": attach.datas,
                    "default_upload_fname": attach.name,
                    "origin": origin,
                }
            )
            ebics_xfer = (
                self.env["ebics.xfer"]
                .with_context(**ctx)
                .with_company(self.company_id)
                .create({})
            )
            ebics_xfer._onchange_ebics_config_id()
            ebics_xfer._onchange_upload_data()
            view = self.env.ref("account_ebics.ebics_xfer_view_form_upload")
            act = {
                "name": _("EBICS Upload"),
                "view_type": "form",
                "view_mode": "form",
                "res_model": "ebics.xfer",
                "view_id": view.id,
                "res_id": ebics_xfer.id,
                "type": "ir.actions.act_window",
                "target": "new",
                "context": ctx,
            }
            return act
