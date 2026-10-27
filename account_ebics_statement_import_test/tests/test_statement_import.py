# Copyright 2026 Noviat.
# License LGPL-3 or later (https://www.gnu.org/licenses/lgpl).

from datetime import date

from odoo.tests import tagged

from odoo.addons.account_ebics.tests.common import (
    IBAN_CA833,
    IBAN_CA879,
    IBAN_CIC,
    IBAN_CMB,
    IBAN_HVB,
    IBAN_LCL,
    IBAN_MULTI,
    EbicsTestCommon,
    FakeEbicsClient,
    read_sample,
)


@tagged("post_install", "-at_install")
class TestStatementImport(EbicsTestCommon):
    """End to end: EBICS file -> split per account -> OCA parser -> statements."""

    def _process(self, sample, file_format, name=None):
        ebics_file = self._create_ebics_file(sample, file_format, name=name)
        ebics_file.process()
        self.assertEqual(ebics_file.state, "done")
        return ebics_file

    def test_cfonb_multi_account(self):
        j1 = self._create_bank_journal("TCA1", IBAN_CA833[0])
        j3 = self._create_bank_journal("TCA3", IBAN_CA833[2])
        ebics_file = self._process("cfonb120_lf_multi_account_05.dat", self.ff_cfonb120)
        statements = ebics_file.bank_statement_ids.sorted("journal_id")
        self.assertEqual(statements.journal_id, j1 | j3)
        st1 = statements.filtered(lambda s: s.journal_id == j1)
        self.assertEqual(st1.balance_start, 8400.0)
        self.assertAlmostEqual(st1.balance_end_real, 8907.45)
        self.assertEqual(sorted(st1.line_ids.mapped("amount")), [-132.55, 640.0])
        self.assertIn("FACT 99812", " ".join(st1.line_ids.mapped("payment_ref")))
        self.assertEqual(set(statements.mapped("import_format")), {"cfonb120"})
        self.assertIn("2 bank statements have been imported", ebics_file.note_process)

    def test_cfonb_minimal_without_complement_lines(self):
        journal = self._create_bank_journal("TCA9", IBAN_CA879[3])
        ebics_file = self._process("cfonb120_lf_minimal_no_05.dat", self.ff_cfonb120)
        statement = ebics_file.bank_statement_ids
        self.assertEqual(statement.journal_id, journal)
        self.assertEqual(len(statement.line_ids), 2)
        self.assertEqual(statement.balance_end_real, 5290.0)

    def test_cfonb_no_line_terminator(self):
        journals = [
            self._create_bank_journal(f"TLC{i}", iban)
            for i, iban in enumerate(IBAN_LCL)
        ]
        ebics_file = self._process(
            "cfonb120_no_eol_multi_account_mixed.dat", self.ff_cfonb120
        )
        self.assertEqual(
            ebics_file.bank_statement_ids.journal_id, journals[1] | journals[3]
        )

    def test_cfonb_complement_lines_in_label(self):
        self._create_bank_journal("TCIC", IBAN_CIC)
        ebics_file = self._process("cfonb120_lf_rich_05.dat", self.ff_cfonb120)
        refs = " ".join(ebics_file.bank_statement_ids.line_ids.mapped("payment_ref"))
        self.assertIn("FACTURE 7731", refs)
        self.assertIn("SALE", refs)

    def test_cfonb_missing_journal_is_reported(self):
        self._create_bank_journal("TCA1", IBAN_CA833[0])
        ebics_file = self._process("cfonb120_lf_multi_account_05.dat", self.ff_cfonb120)
        self.assertEqual(len(ebics_file.bank_statement_ids), 1)
        self.assertIn("No financial journal found", ebics_file.note_process)
        self.assertIn("20000000203", ebics_file.note_process)

    def test_cfonb_empty_file(self):
        self._create_bank_journal("TCMB", IBAN_CMB)
        ebics_file = self._process("cfonb120_no_eol_empty_only.dat", self.ff_cfonb120)
        self.assertFalse(ebics_file.bank_statement_ids)
        self.assertIn("doesn't contain any transaction", ebics_file.note_process)

    def test_camt_fx_entry(self):
        journal = self._create_bank_journal("THVB", IBAN_HVB)
        ebics_file = self._process("camt053_hvb_clav_fx.xml", self.ff_camt053)
        statement = ebics_file.bank_statement_ids
        self.assertEqual(statement.journal_id, journal)
        self.assertEqual(statement.balance_start, 5000.0)
        self.assertEqual(statement.balance_end_real, 3992.5)
        self.assertEqual(sorted(statement.line_ids.mapped("amount")), [-857.5, -150.0])
        self.assertEqual(statement.import_format, "camt053")

    def test_camt_multi_account(self):
        j1 = self._create_bank_journal("TMU1", IBAN_MULTI[0])
        j2 = self._create_bank_journal("TMU2", IBAN_MULTI[1])
        ebics_file = self._process("camt053_multi_account.xml", self.ff_camt053)
        self.assertEqual(ebics_file.bank_statement_ids.journal_id, j1 | j2)

    def test_download_then_process(self):
        journal = self._create_bank_journal("TCMB", IBAN_CMB)
        data = read_sample("cfonb120_no_eol_single_account.dat")
        wizard = self._download_wizard(self.ff_cfonb120, date_to=date(2026, 10, 13))
        with self._fake_client(FakeEbicsClient(downloads={"FDL": data})):
            action = wizard.ebics_download()
        ebics_file = self.env["ebics.file"].browse(action["context"]["ebics_file_ids"])
        ebics_file.process()
        self.assertEqual(ebics_file.bank_statement_ids.journal_id, journal)
        self.assertEqual(len(ebics_file.bank_statement_ids.line_ids), 2)
        self.assertEqual(
            ebics_file.bank_statement_ids.ebics_file_id,
            ebics_file,
        )
