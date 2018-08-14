# -*- coding: utf-8 -*-
# Copyright 2009-2017 Noviat.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models, _
from odoo.exceptions import UserError


class AccountPaymentOrder(models.Model):
    _inherit = 'account.payment.order'

    @api.multi
    def ebics_upload(self):
        self.ensure_one()
        ctx = self._context.copy()
        attach = self.env['ir.attachment'].search(
            [('res_model', '=', self._name),
             ('res_id', '=', self.id)])
        if not attach:
            raise UserError(_(
                "This payment order doesn't contains attachements."
                "\nPlease generate first the Payment Order file first."))
        elif len(attach) > 1:
            raise UserError(_(
                "This payment order contains multiple attachments."
                "\nPlease remove the obsolete attachments or upload "
                "the payment order file via the "
                "EBICS Processing > EBICS Upload menu"))
        else:
            origin = _("Payment Order") + ': ' + self.name
            ctx.update({
                'default_upload_data': attach.datas,
                'default_upload_fname': attach.datas_fname,
                'origin': origin,
            })
            ebics_xfer = self.env['ebics.xfer'].with_context(ctx).create({})
            ebics_xfer._onchange_upload_data()
            ebics_xfer._onchange_format_id()
            view = self.env.ref('account_ebics.ebics_xfer_view_form_upload')
            act = {
                'name': _('EBICS Upload'),
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'ebics.xfer',
                'view_id': view.id,
                'res_id': ebics_xfer.id,
                'type': 'ir.actions.act_window',
                'target': 'new',
                'context': ctx,
            }
            return act
