# Copyright 2025 Noviat.
# License LGPL-3 or later (http://www.gnu.org/licenses/lgpl).

from odoo import fields, models


class AccountPaymentMethod(models.Model):
    _inherit = "account.payment.method"

    ebics_file_format_id = fields.Many2one(
        comodel_name="ebics.file.format",
        string="EBICS File Format",
        help="EBICS file format to pre-select when uploading a batch payment "
        "that uses this payment method.",
    )


class AccountPaymentMethodLine(models.Model):
    _inherit = "account.payment.method.line"

    ebics_file_format_id = fields.Many2one(
        comodel_name="ebics.file.format",
        related="payment_method_id.ebics_file_format_id",
        readonly=False,
        string="EBICS File Format",
    )
