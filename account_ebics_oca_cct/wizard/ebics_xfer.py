# -*- coding: utf-8 -*-
# Copyright 2009-2018 Noviat.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from openerp import models


class EbicsXfer(models.TransientModel):
    _inherit = 'ebics.xfer'

    def _ebics_upload(self):
        payment_order_id = self._context.get('payment_order_id')
        ebics_file = super(EbicsXfer, self)._ebics_upload()
        if ebics_file and payment_order_id:
            order = self.env['payment.order'].browse(payment_order_id)
            order.date_ebics_upload = ebics_file.date
        return ebics_file
