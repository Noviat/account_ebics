# -*- coding: utf-8 -*-
# Copyright 2009-2018 Noviat.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from openerp import fields, models


class PaymentOrder(models.Model):
    _inherit = 'payment.order'

    date_ebics_upload = fields.Date(
        string='EBICS upload date',
        readonly=True)
