# Copyright 2009-2023 Noviat.
# License LGPL-3 or later (http://www.gnu.org/licenses/lgpl).

import logging

from odoo import _, models

_logger = logging.getLogger(__name__)


class AccountStatementImport(models.TransientModel):
    _inherit = "account.statement.import"

    def _check_parsed_data(self, stmts_vals):
        """Basic and structural verifications"""
        if self.env.context.get("active_model") == "ebics.file":
            message = False
            if len(stmts_vals) == 0:
                message = _("This file doesn't contain any statement.")
            if not message:
                no_st_line = True
                for vals in stmts_vals:
                    if vals["transactions"] and len(vals["transactions"]) > 0:
                        no_st_line = False
                        break
                if no_st_line:
                    message = _("This file doesn't contain any transaction.")
                if message:
                    log_msg = (
                        _("Error detected while processing and EBICS File")
                        + ":\n"
                        + message
                    )
                    _logger.warn(log_msg)
                    return
        return super()._check_parsed_data(stmts_vals)

    def _create_bank_statements(self, stmts_vals, result):
        """
        Return error message to ebics.file when handling empty camt.

        Remarks/TODO:
        We could add more info to the message (e.g. date, balance, ...)
        and write this to the ebics.file, note field.
        We could also create empty bank statement (in state done) to clearly
        show days without transactions via the bank statement list view.
        """
        if self.env.context.get("active_model") == "ebics.file":
            messages = []
            transactions = False
            for st_vals in stmts_vals:
                statement_ids = result["statement_ids"][:]
                self._set_statement_name(st_vals)
                if st_vals.get("transactions"):
                    transactions = True
                    super()._create_bank_statements([st_vals], result)
                    if result["statement_ids"] == statement_ids:
                        # no statement has been created, this is the case
                        # when all transactions have been imported already
                        messages.append(
                            _(
                                "Statement %(st_name)s dated %(date)s "
                                "has already been imported.",
                                st_name=st_vals["name"],
                                date=st_vals["date"].strftime("%Y-%m-%d"),
                            )
                        )

            if not transactions:
                messages.append(_("This file doesn't contain any transaction."))
            if messages:
                result["notifications"].append(
                    {"type": "warning", "message": "\n".join(messages)}
                )
        return

    def _set_statement_name(self, st_vals):
        """
        Inherit this method to set your own statement naming policy.
        """
