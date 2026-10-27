# Copyright 2026 Noviat.
# License LGPL-3 or later (https://www.gnu.org/licenses/lgpl).

from odoo.exceptions import UserError
from odoo.tests import tagged

from .common import EbicsTestCommon

IBAN_FOR_COMPANY_TEST = "FR7630004000031234567890143"


@tagged("post_install", "-at_install")
class TestEbicsConfig(EbicsTestCommon):
    def test_update_order_number(self):
        cases = [
            ("A000", "A001"),
            ("A009", "A00A"),
            ("A00Z", "A010"),
            ("A0Z9", "A0ZA"),
            ("AZZZ", "B000"),
            ("ZZZY", "A000"),
            # ZZZZ is accepted by the constraint, it must wrap as well
            ("ZZZZ", "A000"),
        ]
        for current, expected in cases:
            with self.subTest(current=current):
                self.ebics_config._update_order_number(current)
                self.assertEqual(self.ebics_config.order_number, expected)

    def test_order_number_pattern(self):
        for valid in ("A000", "B1Z9", "ZZZZ"):
            with self.subTest(valid=valid):
                self.ebics_config.order_number = valid
        # No 5-character case: Char(size=4) truncates before the constraint runs.
        for invalid in ("a001", "A01", "1000", "A-01"):
            with self.subTest(invalid=invalid), self.assertRaises(UserError):
                self.ebics_config.order_number = invalid

    def test_unlink_confirmed_config_is_blocked(self):
        with self.assertRaises(UserError):
            self.ebics_config.unlink()

    def test_unlink_draft_config(self):
        self.ebics_userid.unlink()
        self.ebics_config.set_to_draft()
        self.ebics_config.unlink()
        self.assertFalse(self.ebics_config.exists())

    def test_company_ids_follow_journals(self):
        journal = self._create_bank_journal("TCMP", IBAN_FOR_COMPANY_TEST)
        self.assertEqual(self.ebics_config.company_ids, journal.company_id)
        self.assertEqual(journal.ebics_config_id, self.ebics_config)
