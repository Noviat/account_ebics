# Copyright 2009-2023 Noviat.
# License LGPL-3 or later (http://www.gnu.org/licenses/lgpl).

from odoo import fields, models


class AccountBankStatement(models.Model):
    _inherit = "account.bank.statement"

    ebics_file_id = fields.Many2one(comodel_name="ebics.file", string="EBICS Data File")
    import_format = fields.Char(readonly=True)
