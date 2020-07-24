# Copyright 2009-2020 Noviat.
# License LGPL-3 or later (http://www.gnu.org/licenses/lpgl).

from odoo import _, models
from odoo.exceptions import UserError


class AccountBatchPayment(models.Model):
    _inherit = "account.batch.payment"

    def ebics_upload(self):
        self.ensure_one()
        ctx = self.env.context.copy()

        origin = _("Batch Payment") + ": " + self.name
        ebics_config = self.env['ebics.config'].search([
            ('journal_ids', '=', self.journal_id.id),
            ('state', '=', 'confirm'),
        ])
        if not ebics_config:
            raise UserError(_(
                "No active EBICS configuration available "
                "for the selected bank."
            ))
        if len(ebics_config) == 1:
            ctx["default_ebics_config_id"] = ebics_config.id
        ctx.update(
            {
                "default_upload_data": self.export_file,
                "default_upload_fname": self.export_filename,
                "origin": origin,
            }
        )

        ebics_xfer = self.env["ebics.xfer"].with_context(ctx).create({})
        ebics_xfer._onchange_ebics_config_id()
        ebics_xfer._onchange_upload_data()
        ebics_xfer._onchange_format_id()
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
