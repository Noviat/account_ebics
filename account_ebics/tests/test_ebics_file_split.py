# Copyright 2026 Noviat.
# License LGPL-3 or later (https://www.gnu.org/licenses/lgpl).

import base64

from lxml import etree

from odoo.tests import tagged

from .common import (
    IBAN_CA833,
    IBAN_CA879,
    IBAN_CIC,
    IBAN_CMB,
    IBAN_HVB,
    IBAN_LCL,
    IBAN_MULTI,
    IBAN_SPK,
    IBAN_SUFFIX,
    EbicsTestCommon,
)


@tagged("post_install", "-at_install")
class TestSplitCfonb(EbicsTestCommon):
    """EBICS files may hold several accounts and empty statements: they are
    split per statement before being handed to the CFONB parser."""

    def _split(self, sample):
        ebics_file = self._create_ebics_file(sample, self.ff_cfonb120)
        res = self._new_res()
        return ebics_file._split_cfonb(res), res

    def _lines(self, st_data):
        return base64.b64decode(st_data["data"]).decode("latin-1").splitlines()

    def test_no_line_terminator_single_account(self):
        """Modelled on Crédit Mutuel de Bretagne: no line terminator at all."""
        journal = self._create_bank_journal("TCMB", IBAN_CMB)
        datas, res = self._split("cfonb120_no_eol_single_account.dat")
        self.assertFalse(res["notifications"])
        self.assertEqual(len(datas), 1)
        self.assertEqual(datas[0]["acc_number"], "10000000101")
        self.assertEqual(datas[0]["journal_id"], journal.id)
        self.assertEqual(datas[0]["company_id"], self.company.id)
        lines = self._lines(datas[0])
        self.assertEqual(
            [x[:2] for x in lines], ["01", "04", "05", "05", "04", "05", "07"]
        )
        self.assertTrue(all(len(x) == 120 for x in lines))

    def test_empty_statements_only(self):
        self._create_bank_journal("TCMB", IBAN_CMB)
        datas, res = self._split("cfonb120_no_eol_empty_only.dat")
        self.assertEqual(datas, [])
        self.assertFalse(res["notifications"])

    def test_multi_account_with_complement_lines(self):
        """Modelled on Crédit Agricole: 3 accounts, the middle one empty, and a
        positive-zero overpunch ('{') on its balance."""
        j1 = self._create_bank_journal("TCA1", IBAN_CA833[0])
        j3 = self._create_bank_journal("TCA3", IBAN_CA833[2])
        datas, res = self._split("cfonb120_lf_multi_account_05.dat")
        self.assertFalse(res["notifications"])
        self.assertEqual([d["journal_id"] for d in datas], [j1.id, j3.id])
        self.assertEqual(
            [x[:2] for x in self._lines(datas[0])],
            ["01", "04", "05", "05", "05", "04", "05", "05", "07"],
        )

    def test_multi_account_missing_journal(self):
        self._create_bank_journal("TCA1", IBAN_CA833[0])
        datas, res = self._split("cfonb120_lf_multi_account_05.dat")
        self.assertEqual(len(datas), 1)
        self.assertEqual(len(res["notifications"]), 1)
        self.assertEqual(res["notifications"][0]["type"], "error")
        self.assertIn("20000000203", res["notifications"][0]["message"])

    def test_no_line_terminator_mixed_empty_and_full(self):
        """Modelled on LCL: 4 accounts, no terminator, empty and full mixed."""
        journals = [
            self._create_bank_journal(f"TLC{i}", iban)
            for i, iban in enumerate(IBAN_LCL)
        ]
        datas, res = self._split("cfonb120_no_eol_multi_account_mixed.dat")
        self.assertFalse(res["notifications"])
        self.assertEqual(
            [d["journal_id"] for d in datas], [journals[1].id, journals[3].id]
        )

    def test_minimal_file_without_complement_lines(self):
        """Modelled on Crédit Agricole 879: no 05 records, an account label in
        the free zone of 01 and dashes in 07, three empty statements before
        the only one with transactions."""
        journal = self._create_bank_journal("TCA9", IBAN_CA879[3])
        datas, res = self._split("cfonb120_lf_minimal_no_05.dat")
        self.assertFalse(res["notifications"])
        self.assertEqual(len(datas), 1)
        self.assertEqual(datas[0]["journal_id"], journal.id)
        self.assertEqual(
            [x[:2] for x in self._lines(datas[0])], ["01", "04", "04", "07"]
        )

    def test_rich_complement_lines_are_kept(self):
        """Modelled on CIC: every 05 qualifier stays with its statement."""
        self._create_bank_journal("TCIC", IBAN_CIC)
        datas, res = self._split("cfonb120_lf_rich_05.dat")
        self.assertFalse(res["notifications"])
        self.assertEqual(len(datas), 1)
        qualifiers = [x[45:48] for x in self._lines(datas[0]) if x[:2] == "05"]
        self.assertEqual(
            qualifiers,
            ["NOM", "RIB", "IBE", "CBE", "LCC", "RCN", "REF", "NPY", "RUM", "LIB"],
        )

    def test_bad_length(self):
        datas, res = self._split("cfonb120_bad_length.dat")
        self.assertEqual(datas, [])
        self.assertEqual(res["notifications"][0]["type"], "error")
        self.assertIn("120", res["notifications"][0]["message"])

    def test_journal_in_other_currency(self):
        usd = self.env.ref("base.USD")
        self._create_bank_journal("TCMB", IBAN_CMB, currency=usd)
        datas, res = self._split("cfonb120_no_eol_single_account.dat")
        self.assertEqual(datas, [])
        self.assertEqual(res["notifications"][0]["type"], "error")


@tagged("post_install", "-at_install")
class TestSplitCamt(EbicsTestCommon):
    def _split(self, sample):
        ebics_file = self._create_ebics_file(sample, self.ff_camt053)
        res = self._new_res()
        return ebics_file._split_camt(res), res

    def _statements(self, st_data):
        root = etree.fromstring(base64.b64decode(st_data["data"]))
        ns = {"ns": root.nsmap[None]}
        return root.xpath("//ns:Stmt/ns:Acct/ns:Id//text()", namespaces=ns)

    def test_single_statement_clav_fx(self):
        """Modelled on UniCredit HVB: OPBD/CLBD/CLAV balances, FX entry."""
        journal = self._create_bank_journal("THVB", IBAN_HVB)
        datas, res = self._split("camt053_hvb_clav_fx.xml")
        self.assertFalse(res["notifications"])
        self.assertEqual(len(datas), 1)
        self.assertEqual(datas[0]["journal_id"], journal.id)
        self.assertEqual(datas[0]["acc_number"], IBAN_HVB)

    def test_multi_account_is_split(self):
        j1 = self._create_bank_journal("TMU1", IBAN_MULTI[0])
        j2 = self._create_bank_journal("TMU2", IBAN_MULTI[1])
        datas, res = self._split("camt053_multi_account.xml")
        self.assertFalse(res["notifications"])
        self.assertEqual([d["journal_id"] for d in datas], [j1.id, j2.id])
        self.assertEqual(self._statements(datas[0]), [IBAN_MULTI[0]])
        self.assertEqual(self._statements(datas[1]), [IBAN_MULTI[1]])

    def test_currency_suffix_is_stripped(self):
        """Built from the code: some banks (e.g. Commerzbank) append the
        currency to the account number."""
        journal = self._create_bank_journal("TSUF", IBAN_SUFFIX)
        datas, res = self._split("camt053_currency_suffix.xml")
        self.assertFalse(res["notifications"])
        self.assertEqual(datas[0]["acc_number"], "0010000005")
        self.assertEqual(datas[0]["journal_id"], journal.id)

    def test_statement_without_entries_is_skipped(self):
        self._create_bank_journal("TSPK", IBAN_SPK)
        datas, res = self._split("camt053_no_entries.xml")
        self.assertEqual(datas, [])
        self.assertFalse(res["notifications"])

    def test_statement_without_account(self):
        datas, res = self._split("camt053_no_account.xml")
        self.assertEqual(datas, [])
        self.assertEqual(res["notifications"][0]["type"], "error")
        self.assertIn(
            "No bank account number found", res["notifications"][0]["message"]
        )

    def test_invalid_xml(self):
        datas, res = self._split("invalid.xml")
        self.assertEqual(datas, [])
        self.assertEqual(res["notifications"][0]["type"], "error")
        self.assertIn("Invalid XML", res["notifications"][0]["message"])


@tagged("post_install", "-at_install")
class TestLookupJournal(EbicsTestCommon):
    def setUp(self):
        super().setUp()
        self.ebics_file = self._create_ebics_file(
            "camt053_sparkasse.xml", self.ff_camt053
        )
        self.res = self._new_res()

    def test_unknown_currency(self):
        currency, journal = self.ebics_file._lookup_journal(
            self.res, "0010000002", "XYZ"
        )
        self.assertFalse(currency)
        self.assertFalse(journal)
        self.assertIn("XYZ", self.res["notifications"][0]["message"])

    def test_no_journal(self):
        currency, journal = self.ebics_file._lookup_journal(
            self.res, "0010000002", "EUR"
        )
        self.assertEqual(currency, self.eur)
        self.assertFalse(journal)
        self.assertEqual(self.res["notifications"][0]["type"], "error")

    def test_journal_currency_match(self):
        expected = self._create_bank_journal("TSPK", IBAN_SPK)
        currency, journal = self.ebics_file._lookup_journal(
            self.res, "0010000002", "eur"
        )
        self.assertEqual(currency, self.eur)
        self.assertEqual(journal, expected)
        self.assertFalse(self.res["notifications"])

    def test_journal_without_currency_uses_company_currency(self):
        expected = self._create_bank_journal("TSPK", IBAN_SPK)
        expected.sudo().currency_id = False
        code = self.company.currency_id.name
        currency, journal = self.ebics_file._lookup_journal(
            self.res, "0010000002", code
        )
        self.assertEqual(currency, self.company.currency_id)
        self.assertEqual(journal, expected)
