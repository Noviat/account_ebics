# Copyright 2009-2024 Noviat.
# License LGPL-3 or later (http://www.gnu.org/licenses/lpgl).

from odoo import fields, models


class AccountPaymentMode(models.Model):
    _inherit = "account.payment.mode"

    ebics_format_id = fields.Many2one(
        comodel_name="ebics.file.format",
        string="EBICS File Format",
        domain="[('type', '=', 'up')]",
        help="Select EBICS File Format to upload.",
    )
