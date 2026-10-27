# Copyright 2026 Noviat.
# License LGPL-3 or later (https://www.gnu.org/licenses/lgpl).

import base64

from odoo.exceptions import UserError
from odoo.tests import tagged

from odoo.addons.account_ebics.tests.common import EbicsTestCommon, FakeEbicsClient


@tagged("post_install", "-at_install")
class TestPaymentOrderUpload(EbicsTestCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.user.groups_id |= cls.env.ref(
            "account_payment_order.group_account_payment"
        )
        cls.journal = cls._create_bank_journal("TPO", "FR7630004000031234567890143")
        cls.ff_cct = cls.env.ref("account_ebics.ebics_ff_CCT")
        cls.mode = cls.env["account.payment.mode"].create(
            {
                "name": "EBICS credit transfer",
                "company_id": cls.company.id,
                "bank_account_link": "fixed",
                "fixed_journal_id": cls.journal.id,
                "payment_method_id": cls.env.ref(
                    "account.account_payment_method_manual_out"
                ).id,
                "ebics_format_id": cls.ff_cct.id,
            }
        )

    def _order(self, state="generated", with_file=True):
        order = self.env["account.payment.order"].create(
            {
                "payment_type": "outbound",
                "payment_mode_id": self.mode.id,
                "journal_id": self.journal.id,
            }
        )
        order.state = state
        if with_file:
            self._attach(order, "pain001.xml")
        return order

    def _attach(self, order, name):
        return self.env["ir.attachment"].create(
            {
                "name": name,
                "res_model": order._name,
                "res_id": order.id,
                "datas": base64.b64encode(b"<Document>pain.001</Document>"),
            }
        )

    def test_hide_ebics_upload(self):
        self.assertTrue(self._order(state="draft").hide_ebics_upload)
        self.assertFalse(self._order().hide_ebics_upload)
        self.ebics_config.journal_ids = False
        self.assertTrue(self._order().hide_ebics_upload)

    def test_upload_requires_format_on_mode(self):
        self.mode.ebics_format_id = False
        with self.assertRaisesRegex(UserError, "EBICS File Format"):
            self._order().ebics_upload()

    def test_upload_requires_one_file(self):
        with self.assertRaisesRegex(UserError, "doesn't contain attachments"):
            self._order(with_file=False).ebics_upload()
        order = self._order()
        self._attach(order, "pain001_old.xml")
        with self.assertRaisesRegex(UserError, "multiple attachments"):
            order.ebics_upload()

    def test_upload(self):
        order = self._order()
        # the form button passes the active model, as the web client does
        action = order.with_context(
            active_model=order._name, active_id=order.id
        ).ebics_upload()
        wizard = self.env["ebics.xfer"].browse(action["res_id"])
        self.assertEqual(wizard.ebics_config_id, self.ebics_config)
        self.assertEqual(wizard.ebics_userid_id, self.ebics_userid)
        self.assertEqual(wizard.format_id, self.ff_cct)
        self.assertEqual(wizard.upload_fname, "pain001.xml")
        with self._fake_client(FakeEbicsClient(order_id="N077")) as client:
            wizard.with_context(**action["context"]).ebics_upload()
        self.assertEqual(client.uploads[0][1], b"<Document>pain.001</Document>")
        self.assertEqual(order.state, "uploaded")
        self.assertEqual(order.ebics_order_number, "N077")
        self.assertEqual(order.ebics_file_id.pain_state, "uploaded")
        self.assertIn(f"Payment Order: {order.name}", order.ebics_file_id.note)
        self.assertTrue(any("N077" in msg.body for msg in order.message_ids))
