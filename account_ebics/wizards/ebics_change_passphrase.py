# Copyright 2009-2024 Noviat.
# License LGPL-3 or later (http://www.gnu.org/licenses/lgpl).

import logging

from odoo import _, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

try:
    import fintech
    from fintech.ebics import EbicsKeyRing

    fintech.cryptolib = "cryptography"
except ImportError:
    _logger.warning("Failed to import fintech")


class EbicsChangePassphrase(models.TransientModel):
    _name = "ebics.change.passphrase"
    _description = "Change EBICS keys passphrase"

    ebics_userid_id = fields.Many2one(
        comodel_name="ebics.userid", string="EBICS UserID", readonly=True
    )
    old_pass = fields.Char(string="Old Passphrase")
    new_pass = fields.Char(string="New Passphrase")
    new_pass_check = fields.Char(string="New Passphrase (verification)")
    old_sig_pass = fields.Char(string="Old Signature Passphrase")
    new_sig_pass = fields.Char(string="New Signature Passphrase")
    new_sig_pass_check = fields.Char(string="New Signature Passphrase (verification)")
    ebics_sig_passphrase_invisible = fields.Boolean(
        compute="_compute_ebics_sig_passphrase_invisible"
    )
    note = fields.Text(string="Notes", readonly=True)

    def _compute_ebics_sig_passphrase_invisible(self):
        for rec in self:
            if fintech.__version_info__ < (7, 3, 1):
                rec.ebics_sig_passphrase_invisible = True
            else:
                rec.ebics_sig_passphrase_invisible = False

    def change_passphrase(self):
        self.ensure_one()
        self.note = ""
        if (
            self.ebics_userid_id.ebics_passphrase_store
            and self.old_pass
            and self.old_pass != self.ebics_userid_id.ebics_passphrase
        ):
            raise UserError(_("Incorrect old passphrase."))
        if self.new_pass != self.new_pass_check:
            raise UserError(_("New passphrase verification error."))
        if self.new_pass and self.new_pass == self.ebics_userid_id.ebics_passphrase:
            raise UserError(_("New passphrase equal to old passphrase."))
        if (
            self.new_sig_pass
            and self.old_sig_pass
            and self.new_sig_pass == self.old_sig_pass
        ):
            raise UserError(
                _("New signature passphrase equal to old signature passphrase.")
            )
        if self.new_sig_pass != self.new_sig_pass_check:
            raise UserError(_("New signature passphrase verification error."))
        passphrase = (
            self.ebics_userid_id.ebics_passphrase_store
            and self.ebics_userid_id.ebics_passphrase
            or self.old_pass
        )
        try:
            keyring_params = {
                "keys": self.ebics_userid_id.ebics_keys_fn,
                "passphrase": passphrase,
            }
            if self.new_sig_pass:
                keyring_params["sig_passphrase"] = self.old_sig_pass or None
            keyring = EbicsKeyRing(**keyring_params)
            change_params = {}
            if self.new_pass:
                change_params["passphrase"] = self.new_pass
            if self.new_sig_pass:
                change_params["sig_passphrase"] = self.new_sig_pass
            if change_params:
                keyring.change_passphrase(**change_params)
        except (ValueError, RuntimeError) as err:
            raise UserError(str(err)) from err

        if self.new_pass:
            self.ebics_userid_id.ebics_passphrase = (
                self.ebics_userid_id.ebics_passphrase_store and self.new_pass
            )
            self.note += "The EBICS Passphrase has been changed."
        if self.new_sig_pass:
            # removing ebics_sig_passphrase from db should not be required
            # but we do it for double safety
            if self.ebics_userid_id.ebics_sig_passphrase:
                self.ebics_userid_id.ebics_sig_passphrase = False
            self.note += "The EBICS Signature Passphrase has been changed."

        module = __name__.split("addons.")[1].split(".")[0]
        result_view = self.env.ref(
            "%s.ebics_change_passphrase_view_form_result" % module
        )
        return {
            "name": _("EBICS Keys Change Passphrase"),
            "res_id": self.id,
            "view_type": "form",
            "view_mode": "form",
            "res_model": "ebics.change.passphrase",
            "view_id": result_view.id,
            "target": "new",
            "type": "ir.actions.act_window",
        }

    def button_close(self):
        self.ensure_one()
        return {"type": "ir.actions.act_window_close"}
