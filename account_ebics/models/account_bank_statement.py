# Copyright 2009-2020 Noviat.
# License LGPL-3 or later (http://www.gnu.org/licenses/lpgl).

from odoo import fields, models


class AccountBankStatement(models.Model):
    _inherit = 'account.bank.statement'

    ebics_file_id = fields.Many2one(
        comodel_name='ebics.file', string='EBICS Data File')
