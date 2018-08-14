# -*- coding: utf-8 -*-
# Copyright 2009-2017 Noviat.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from openerp import api, models, _


class BankingExportSepaWizard(models.TransientModel):
    _inherit = 'banking.export.sepa.wizard'

    @api.multi
    def ebics_upload(self):
        self.ensure_one()
        ctx = self._context.copy()
        payment_order = self.payment_order_ids[0]
        origin = _("Payment Order") + ': ' + payment_order.reference
        ctx.update({
            'default_upload_data': self.file,
            'default_upload_fname': self.filename,
            'origin': origin,
            'payment_order_id': payment_order.id,
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
