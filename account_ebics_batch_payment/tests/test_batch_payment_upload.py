# Copyright 2026 Noviat.
# License LGPL-3 or later (https://www.gnu.org/licenses/lgpl).

import base64
from unittest.mock import patch

from odoo.exceptions import UserError
from odoo.tests import tagged

from odoo.addons.account_ebics.tests.common import EbicsTestCommon, FakeEbicsClient


@tagged("post_install", "-at_install")
class TestBatchPaymentUpload(EbicsTestCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.journal = cls._create_bank_journal("TBP", "FR7630004000031234567890143")
        cls.ff_cct = cls.env.ref("account_ebics.ebics_ff_CCT")
        cls.method = cls.env.ref("account.account_payment_method_manual_out")

    def _batch(self, state="sent"):
        batch = self.env["account.batch.payment"].create(
            {
                "journal_id": self.journal.id,
                "batch_type": "outbound",
                "payment_method_id": self.method.id,
                "export_file": base64.b64encode(b"<Document>pain.001</Document>"),
                "export_filename": "batch.xml",
            }
        )
        # Without payments the batch stays in draft: set the state directly.
        batch.state = state
        return batch

    def _generating_files(self):
        batch_class = type(self.env["account.batch.payment"])
        return patch.object(
            batch_class, "_get_methods_generating_files", return_value=["manual"]
        )

    def test_hide_ebics_upload(self):
        with self._generating_files():
            self.assertFalse(self._batch().hide_ebics_upload)
            self.assertTrue(self._batch(state="draft").hide_ebics_upload)
            batch = self._batch()
            batch.ebics_file_id = self.env["ebics.file"].create(
                {"name": "batch.xml", "date": "2026-10-13", "pain_state": "uploaded"}
            )
            self.assertTrue(batch.hide_ebics_upload)
        # no file generation for this payment method
        self.assertTrue(self._batch().hide_ebics_upload)

    def test_upload_requires_ebics_config(self):
        self.ebics_config.journal_ids = False
        with self.assertRaises(UserError):
            self._batch().ebics_upload()

    def test_upload_format_from_payment_method(self):
        self.method.ebics_file_format_id = self.ff_cct
        action = self._batch().ebics_upload()
        wizard = self.env["ebics.xfer"].browse(action["res_id"])
        self.assertEqual(wizard.format_id, self.ff_cct)
        self.assertEqual(wizard.upload_fname, "batch.xml")

    def test_upload(self):
        self.method.ebics_file_format_id = self.ff_cct
        batch = self._batch()
        action = batch.ebics_upload()
        wizard = self.env["ebics.xfer"].browse(action["res_id"])
        with self._fake_client(FakeEbicsClient(order_id="N088")) as client:
            wizard.with_context(**action["context"]).ebics_upload()
        self.assertEqual(client.uploads[0][1], b"<Document>pain.001</Document>")
        self.assertEqual(batch.ebics_order_number, "N088")
        self.assertEqual(batch.ebics_pain_state, "uploaded")
        self.assertIn(f"Batch Payment: {batch.name}", batch.ebics_file_id.note)
        self.assertTrue(any("N088" in msg.body for msg in batch.message_ids))
