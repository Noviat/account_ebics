# Copyright 2026 Noviat.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from unittest.mock import patch

from fintech.ebics import EbicsTechnicalError

from odoo.exceptions import UserError
from odoo.tests import tagged

from odoo.addons.account_ebics.tests.common import (
    EbicsTestCommon,
    FakeEbicsClient,
    read_sample,
)


@tagged("post_install", "-at_install")
class TestEbicsBatchImport(EbicsTestCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # A format without processing method: files are stored as done.
        cls.ff_ptk = cls.env["ebics.file.format"].create(
            {"name": "PTK", "type": "down", "order_type": "PTK", "suffix": "txt"}
        )
        cls.ebics_config.ebics_file_format_ids = cls.ff_ptk
        cls.log_model = cls.env["ebics.batch.log"]

    def _run(self, client, **kwargs):
        with self._fake_client(client):
            self.log_model._batch_import(
                ebics_config_ids=self.ebics_config.ids, **kwargs
            )
        return self.log_model.search([], order="id desc", limit=1)

    def test_import(self):
        client = FakeEbicsClient(downloads={"PTK": read_sample("ptk_protocol.txt")})
        log = self._run(client, date_from="2026-10-12", date_to="2026-10-13")
        self.assertEqual(log.state, "done")
        self.assertEqual(log.ebics_config_ids, self.ebics_config)
        self.assertEqual(log.file_count, 1)
        self.assertEqual(log.file_ids.name, "TESTHOST_PARTNER1_2026-10-13.txt")
        self.assertEqual(log.log_ids.state, "done")
        self.assertEqual(log.log_ids.error_count, 0)

    def test_import_prefers_transport_signature_user(self):
        """Downloads need no signature right: a class T user is preferred."""
        self.ebics_userid.signature_class = "E"
        transport_userid = self.ebics_userid.copy(
            {"name": "USER2", "signature_class": "T", "state": "active_keys"}
        )
        client = FakeEbicsClient(downloads={"PTK": read_sample("ptk_protocol.txt")})
        log = self._run(client, date_to="2026-10-13")
        self.assertEqual(log.file_ids.ebics_userid_id, transport_userid)

    def test_import_transfer_error(self):
        error = EbicsTechnicalError("061001", "EBICS_AUTHENTICATION_FAILED")
        log = self._run(FakeEbicsClient(error=error))
        self.assertEqual(log.state, "error")
        self.assertFalse(log.file_ids)
        self.assertEqual(log.log_ids.error_count, 1)
        self.assertIn("EBICS_AUTHENTICATION_FAILED", log.log_ids.note)

    def test_import_draft_config(self):
        self.ebics_config.set_to_draft()
        log = self._run(FakeEbicsClient())
        self.assertEqual(log.state, "error")
        self.assertIn("Please set state to 'Confirm'", log.log_ids.note)

    def test_import_without_stored_passphrase(self):
        self.ebics_userid.ebics_passphrase_store = False
        log = self._run(FakeEbicsClient())
        self.assertEqual(log.state, "error")
        self.assertIn("No EBICS UserID with stored passphrase", log.log_ids.note)

    def test_draft_files_are_processed_and_reprocessed(self):
        ebics_file = self._create_ebics_file("camt053_sparkasse.xml", self.ff_camt053)
        log = self.log_model.create({"file_ids": [(6, 0, ebics_file.ids)]})
        self.assertTrue(log.has_draft_files)
        file_class = type(ebics_file)
        with patch.object(file_class, "process", autospec=True) as process:
            log.reprocess()
        process.assert_called_once_with(ebics_file)
        # the file is still draft since processing was mocked
        self.assertEqual(log.state, "draft")

    def test_unlink_only_draft_logs(self):
        log = self.log_model.create({})
        log.button_done()
        with self.assertRaises(UserError):
            log.unlink()
        log.button_draft()
        log.unlink()
        self.assertFalse(log.exists())
