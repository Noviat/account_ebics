# Copyright 2009-2020 Noviat.
# License LGPL-3 or later (http://www.gnu.org/licenses/lpgl).

import logging

from odoo import models, _

_logger = logging.getLogger(__name__)


class AccountBankStatementImport(models.TransientModel):
    _inherit = 'account.bank.statement.import'

    def _check_parsed_data(self, stmts_vals, account_number):
        """ Basic and structural verifications """
        if self.env.context.get('active_model') == 'ebics.file':
            message = False
            if len(stmts_vals) == 0:
                message = _("This file doesn't contain any statement.")
            if not message:
                no_st_line = True
                for vals in stmts_vals:
                    if vals['transactions'] and len(vals['transactions']) > 0:
                        no_st_line = False
                        break
                if no_st_line:
                    message = _('This file doesn\'t contain any transaction.')
                if message:
                    log_msg = _(
                        "Error detected while processing and EBICS File"
                    ) + ':\n' + message
                    _logger.warn(log_msg)
                    return
        super()._check_parsed_data(stmts_vals, account_number)

    def _create_bank_statements(self, stmts_vals):
        """
        Return error message to ebics.file when handling empty camt.

        Remarks/TODO:
        We could add more info to the message (e.g. date, balance, ...)
        and write this to the ebics.file, note field.
        We could also create empty bank statement (in state done) to clearly
        show days without transactions via the bank statement list view.
        """
        if self.env.context.get('active_model') == 'ebics.file':
            transactions = False
            for st_vals in stmts_vals:
                if st_vals.get('transactions'):
                    transactions = True
                    break
            if not transactions:
                message = _('This file doesn\'t contain any transaction.')
                st_line_ids = []
                notifications = {
                    'type': 'warning',
                    'message': message,
                    'details': ''
                }
                return st_line_ids, [notifications]

        return super()._create_bank_statements(stmts_vals)
