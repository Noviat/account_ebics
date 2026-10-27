# Copyright 2026 Noviat.
# License LGPL-3 or later (https://www.gnu.org/licenses/lgpl).

from unittest.mock import patch

from odoo import Command
from odoo.exceptions import UserError
from odoo.tests import tagged

from .common import IBAN_SPK, EbicsTestCommon


@tagged("post_install", "-at_install")
class TestEbicsFile(EbicsTestCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.journal = cls._create_bank_journal("TSPK", IBAN_SPK)

    def _statement(self, name, date="2026-10-13", import_format="camt053"):
        statement = self.env["account.bank.statement"].create(
            {
                "name": name,
                "journal_id": self.journal.id,
                "line_ids": [
                    Command.create(
                        {
                            "journal_id": self.journal.id,
                            "date": date,
                            "payment_ref": f"line {name}",
                            "amount": 10.0,
                        }
                    )
                ],
            }
        )
        statement.import_format = import_format
        return statement

    def test_duplicate_statement_is_removed(self):
        self._statement("ST-1")
        duplicate = self._statement("ST-1")
        res = self._new_res()
        res["statement_ids"] = duplicate.ids
        ebics_file = self._create_ebics_file("camt053_sparkasse.xml", self.ff_camt053)
        kept = ebics_file._statement_duplicate_check(res, duplicate)
        self.assertFalse(kept)
        self.assertFalse(duplicate.exists())
        self.assertEqual(res["statement_ids"], [])
        self.assertEqual(res["notifications"][0]["type"], "warning")
        self.assertIn("ST-1", res["notifications"][0]["message"])

    def test_duplicate_check_scope(self):
        """A checked statement only collides with the same name, date and format."""
        # existing statements: same name, other date / same name, other format
        self._statement("ST-2", date="2026-10-14")
        self._statement("ST-2", import_format="cfonb120")
        new = self._statement("ST-2")
        # outside DUP_CHECK_FORMATS: never checked
        unchecked = self._statement("ST-2", import_format="camt052")
        statements = new | unchecked
        res = self._new_res()
        res["statement_ids"] = statements.ids
        ebics_file = self._create_ebics_file("camt053_sparkasse.xml", self.ff_camt053)
        kept = ebics_file._statement_duplicate_check(res, statements)
        self.assertEqual(kept, statements)
        self.assertFalse(res["notifications"])

    def test_process_result_note(self):
        ebics_file = self._create_ebics_file("camt053_sparkasse.xml", self.ff_camt053)
        ebics_file.note_process = ""
        statement = self._statement("ST-3")
        res = {
            "statement_ids": statement.ids,
            "notifications": [
                {"type": "error", "message": "Broken entry", "details": "line 4"},
                {"type": "warning", "message": "Odd balance"},
                {"info": "Something to know"},
                "Plain text warning",
            ],
        }
        ebics_file._process_download_result(res, file_format="camt053")
        note = ebics_file.note_process
        self.assertIn("Broken entry\nline 4", note)
        self.assertIn("Number of errors: 1", note)
        self.assertIn("Number of warnings: 3", note)
        self.assertIn("1 bank statement has been imported", note)
        self.assertEqual(ebics_file.bank_statement_ids, statement)
        self.assertEqual(statement.import_format, "camt053")
        self.assertEqual(ebics_file.company_ids, self.company)

    def test_process_result_empty_file(self):
        ebics_file = self._create_ebics_file("camt053_sparkasse.xml", self.ff_camt053)
        ebics_file.note_process = ""
        ebics_file._process_download_result(self._new_res(), file_format="camt053")
        self.assertIn("doesn't contain any transaction", ebics_file.note_process)

    def test_unlink_done_file_is_blocked(self):
        ebics_file = self._create_ebics_file("camt053_sparkasse.xml", self.ff_camt053)
        ebics_file.set_to_done()
        with self.assertRaises(UserError):
            ebics_file.unlink()

    def test_unlink_removes_statements(self):
        ebics_file = self._create_ebics_file("camt053_sparkasse.xml", self.ff_camt053)
        statement = self._statement("ST-4")
        statement.ebics_file_id = ebics_file
        ebics_file.unlink()
        self.assertFalse(statement.exists())

    def test_unlink_pain002_file(self):
        """pain.002 processing is a placeholder: its files must stay removable."""
        ebics_file = self._create_ebics_file(
            "ptk_protocol.txt", self.env.ref("account_ebics.ebics_ff_Z01")
        )
        ebics_file.unlink()
        self.assertFalse(ebics_file.exists())

    def test_process_format_without_method(self):
        """Modelled on a Sparkasse customer protocol (PTK): stored, not processed."""
        ptk = self.env["ebics.file.format"].create(
            {"name": "PTK", "type": "down", "order_type": "PTK", "suffix": "txt"}
        )
        ebics_file = self._create_ebics_file("ptk_protocol.txt", ptk)
        with self.assertRaisesRegex(UserError, "no support"):
            ebics_file.process()

    def test_check_import_module(self):
        ebics_file = self._create_ebics_file("camt053_sparkasse.xml", self.ff_camt053)
        self.assertTrue(ebics_file._check_import_module("account_ebics"))
        self.assertFalse(
            ebics_file._check_import_module("no_such_module", raise_if_not_found=False)
        )
        with self.assertRaises(UserError):
            ebics_file._check_import_module("no_such_module")

    def test_enterprise_import_does_not_commit_in_tests(self):
        """The Enterprise path commits after each statement in production."""
        ebics_file = self._create_ebics_file("camt053_sparkasse.xml", self.ff_camt053)
        statement = self._statement("ST-5")
        st_datas = [{"acc_number": "0010000002", "journal_id": self.journal.id}]

        def create_statement(res, st_data):
            res["statement_ids"].append(statement.id)

        file_class = type(ebics_file)
        cursor_class = type(self.env.cr)
        res = self._new_res()
        with (
            patch.object(
                file_class, "_create_bank_statement_oe", side_effect=create_statement
            ),
            patch.object(cursor_class, "commit", side_effect=AssertionError("commit")),
        ):
            ebics_file._process_bank_statement_oe(res, st_datas)
        self.assertEqual(res["statement_ids"], statement.ids)
        self.assertFalse(res["notifications"])

    def test_enterprise_import_reports_errors(self):
        ebics_file = self._create_ebics_file("camt053_sparkasse.xml", self.ff_camt053)
        st_datas = [{"acc_number": "0010000002", "journal_id": self.journal.id}]
        res = self._new_res()
        with patch.object(
            type(ebics_file),
            "_create_bank_statement_oe",
            side_effect=UserError("Journal mismatch"),
        ):
            ebics_file._process_bank_statement_oe(res, st_datas)
        self.assertIn("Journal mismatch", res["notifications"][0]["message"])
        self.assertIn("0010000002", res["notifications"][0]["message"])
