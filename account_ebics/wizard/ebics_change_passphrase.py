# Copyright 2009-2019 Noviat.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import logging

from odoo import api, fields, models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

try:
    import fintech
    from fintech.ebics import EbicsKeyRing
    fintech.cryptolib = 'cryptography'
except ImportError:
    _logger.warning('Failed to import fintech')


class EbicsChangePassphrase(models.TransientModel):
    _name = 'ebics.change.passphrase'
    _description = 'Change EBICS keys passphrase'

    ebics_config_id = fields.Many2one(
        comodel_name='ebics.config',
        string='EBICS Configuration',
        readonly=True)
    old_pass = fields.Char(
        string='Old Passphrase',
        required=True)
    new_pass = fields.Char(
        string='New Passphrase',
        required=True)
    new_pass_check = fields.Char(
        string='New Passphrase (verification)',
        required=True)
    note = fields.Text(string='Notes', readonly=True)

    @api.multi
    def change_passphrase(self):
        self.ensure_one()
        if self.old_pass != self.ebics_config_id.ebics_passphrase:
            raise UserError(_(
                "Incorrect old passphrase."))
        if self.new_pass != self.new_pass_check:
            raise UserError(_(
                "New passphrase verification error."))
        if self.new_pass == self.ebics_config_id.ebics_passphrase:
            raise UserError(_(
                "New passphrase equal to old passphrase."))
        try:
            keyring = EbicsKeyRing(
                keys=self.ebics_config_id.ebics_keys,
                passphrase=self.ebics_config_id.ebics_passphrase)
            keyring.change_passphrase(self.new_pass)
        except ValueError as e:
            raise UserError(str(e))
        self.ebics_config_id.ebics_passphrase = self.new_pass
        self.note = "The EBICS Passphrase has been changed."

        module = __name__.split('addons.')[1].split('.')[0]
        result_view = self.env.ref(
            '%s.ebics_change_passphrase_view_form_result' % module)
        return {
            'name': _('EBICS Keys Change Passphrase'),
            'res_id': self.id,
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'ebics.change.passphrase',
            'view_id': result_view.id,
            'target': 'new',
            'type': 'ir.actions.act_window',
        }

    @api.multi
    def button_close(self):
        self.ensure_one()
        return {'type': 'ir.actions.act_window_close'}
