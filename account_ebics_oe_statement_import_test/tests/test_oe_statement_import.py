# Copyright 2026 Noviat.
# License LGPL-3 or later (https://www.gnu.org/licenses/lgpl).

from unittest.mock import patch

from odoo.tests import tagged

from odoo.addons.account_ebics.tests.common import (
    IBAN_HVB,
    IBAN_MULTI,
    EbicsTestCommon,
)


@tagged("post_install", "-at_install")
class TestOeStatementImport(EbicsTestCommon):
    """End to end through the Odoo Enterprise camt import: EBICS file ->
    split per account -> ir.attachment -> journal._import_bank_statement."""

    def _enterprise_parser_only(self):
        """Both camt parsers are installed in the Enterprise CI job and
        _process_camt053 prefers the OCA one: hide it."""
        file_class = type(self.env["ebics.file"])
        check_import_module = file_class._check_import_module

        def check(record, module, raise_if_not_found=True):
            if module == "account_statement_import_camt":
                return False
            return check_import_module(record, module, raise_if_not_found)

        return patch.object(file_class, "_check_import_module", check)

    def _process(self, sample, name=None):
        ebics_file = self._create_ebics_file(sample, self.ff_camt053, name=name)
        with self._enterprise_parser_only():
            ebics_file.process()
        self.assertEqual(ebics_file.state, "done")
        return ebics_file

    def test_camt_statement(self):
        journal = self._create_bank_journal("THVB", IBAN_HVB)
        ebics_file = self._process("camt053_hvb_clav_fx.xml")
        statement = ebics_file.bank_statement_ids
        self.assertEqual(statement.journal_id, journal)
        self.assertEqual(statement.balance_start, 5000.0)
        self.assertEqual(statement.balance_end_real, 3992.5)
        self.assertEqual(sorted(statement.line_ids.mapped("amount")), [-857.5, -150.0])
        self.assertEqual(statement.import_format, "camt053")
        self.assertIn("1 bank statement has been imported", ebics_file.note_process)

    def test_camt_multi_account(self):
        j1 = self._create_bank_journal("TMU1", IBAN_MULTI[0])
        j2 = self._create_bank_journal("TMU2", IBAN_MULTI[1])
        ebics_file = self._process("camt053_multi_account.xml")
        self.assertEqual(ebics_file.bank_statement_ids.journal_id, j1 | j2)
        self.assertIn("2 bank statements have been imported", ebics_file.note_process)

    def test_reimport_is_reported(self):
        self._create_bank_journal("THVB", IBAN_HVB)
        sample = "camt053_hvb_clav_fx.xml"
        first = self._process(sample, name="first.xml")
        self.assertEqual(len(first.bank_statement_ids), 1)
        second = self._process(sample, name="second.xml")
        self.assertFalse(second.bank_statement_ids)
        self.assertIn("has not been processed", second.note_process)
        self.assertIn("0010000001", second.note_process)
