# Copyright 2026 Noviat.
# License LGPL-3 or later (https://www.gnu.org/licenses/lgpl).

import base64
from unittest.mock import patch

from odoo.exceptions import UserError
from odoo.tests import tagged

from odoo.addons.account_ebics.wizards import ebics_xfer as ebics_xfer_module

from .test_ebics_userid import EbicsKeysCommon

# Throwaway passphrase for keys created in a temporary directory.
WRONG_PHRASE = "wrong-passphrase"


def capturing_client(captured, init_error=None):
    """Stand-in for fintech's EbicsClient that records the real EbicsBank and
    EbicsUser built by ebics.xfer._setup_client."""

    class CapturingClient:
        def __init__(self, bank, user, version=None):
            if init_error:
                raise init_error
            captured.update(bank=bank, user=user, version=version)
            self.bank = bank

        def FUL(self, filetype, data, **kwargs):
            # As fintech does on H003: the OrderID comes from the bank object.
            return self.bank._next_order_id(captured["user"].partnerid)

    return CapturingClient


@tagged("post_install", "-at_install")
class TestSetupClient(EbicsKeysCommon):
    """ebics.xfer._setup_client with real keys; only the transport is faked."""

    def setUp(self):
        super().setUp()
        self.userid = self._new_userid()
        self._init_1(self.userid)
        self.userid.state = "active_keys"
        self.ff_ful = self.env.ref("account_ebics.ebics_ff_LCR")

    def _wizard(self, file_format=None, **vals):
        return self.env["ebics.xfer"].create(
            {
                "ebics_config_id": self.ebics_config.id,
                "ebics_userid_id": self.userid.id,
                "format_id": (file_format or self.ff_ful).id,
                "upload_data": base64.b64encode(b"LCR DATA"),
                "upload_fname": "lcr.txt",
                "note": "",
                **vals,
            }
        )

    def _setup(self, wizard, init_error=None):
        captured = {}
        client_class = capturing_client(captured, init_error=init_error)
        with patch.object(ebics_xfer_module, "EbicsClient", client_class):
            client = wizard._setup_client()
        return client, captured

    def test_client_from_config_and_keys(self):
        client, captured = self._setup(self._wizard())
        self.assertTrue(client)
        self.assertEqual(captured["version"], "H004")
        self.assertEqual(captured["bank"].hostid, "TESTHOST")
        self.assertEqual(captured["bank"].url, "https://ebics.example.invalid/ebics")
        self.assertEqual(captured["user"].partnerid, "PARTNER1")
        self.assertEqual(captured["user"].userid, self.userid.name)

    def test_signature_class(self):
        cases = [
            # (userid default, file format override, expected transport_only)
            ("T", False, True),
            ("E", False, False),
            ("T", "E", False),
            ("E", "T", True),
        ]
        for user_class, format_class, expected in cases:
            with self.subTest(user=user_class, file_format=format_class):
                self.userid.signature_class = user_class
                self.ff_ful.signature_class = format_class
                _client, captured = self._setup(self._wizard())
                self.assertEqual(captured["user"].transport_only, expected)

    def test_h003_order_number_is_given_to_the_bank(self):
        self.ebics_config.write({"ebics_version": "H003", "order_number": "B00Z"})
        wizard = self._wizard()
        captured = {}
        with patch.object(ebics_xfer_module, "EbicsClient", capturing_client(captured)):
            ebics_file = wizard._ebics_upload()
        self.assertEqual(ebics_file.ebics_order_number, "B00Z")
        self.assertEqual(self.ebics_config.order_number, "B010")

    def test_wrong_passphrase(self):
        wizard = self._wizard(ebics_passphrase=WRONG_PHRASE)
        with self.assertRaisesRegex(UserError, "Error while accessing the EBICS Keys"):
            self._setup(wizard)

    def test_missing_keys_directory(self):
        self.ebics_config.ebics_keys = "/nonexistent/ebics_keys"
        with self.assertRaisesRegex(UserError, "is not available"):
            self._setup(self._wizard())

    def test_client_creation_error(self):
        wizard = self._wizard()
        client, _captured = self._setup(wizard, init_error=RuntimeError("bad url"))
        self.assertFalse(client)
        self.assertIn("Unknown Error", wizard.note)
        self.assertIn("bad url", wizard.note)
