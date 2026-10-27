# Copyright 2026 Noviat.
# License LGPL-3 or later (https://www.gnu.org/licenses/lgpl).

import pprint
from unittest.mock import patch

from fintech.ebics import EbicsFunctionalError, EbicsKeyRing, EbicsTechnicalError

from odoo.exceptions import UserError
from odoo.tests import tagged

from .test_ebics_userid import EbicsKeysCommon

# Test passphrases for throwaway keys created in a temporary directory.
INIT_PHRASE = "init-passphrase"
NEXT_PHRASE = "next-passphrase"
OTHER_PHRASE = "other-passphrase"
WRONG_PHRASE = "wrong-passphrase"


@tagged("post_install", "-at_install")
class TestChangePassphrase(EbicsKeysCommon):
    def setUp(self):
        super().setUp()
        self.userid = self._new_userid()
        self._init_1(self.userid)

    def _change(self, **vals):
        wizard = self.env["ebics.change.passphrase"].create(
            {"ebics_userid_id": self.userid.id, **vals}
        )
        wizard.change_passphrase()
        return wizard

    def test_change_passphrase(self):
        wizard = self._change(
            old_pass=INIT_PHRASE,
            new_pass=NEXT_PHRASE,
            new_pass_check=NEXT_PHRASE,
        )
        self.assertEqual(self.userid.ebics_passphrase, NEXT_PHRASE)
        self.assertIn("has been changed", wizard.note)
        keyring = EbicsKeyRing(keys=self.userid.ebics_keys_fn, passphrase=NEXT_PHRASE)
        self.assertTrue(keyring["#USER"])

    def test_wrong_old_passphrase(self):
        with self.assertRaisesRegex(UserError, "Incorrect old passphrase"):
            self._change(
                old_pass=WRONG_PHRASE,
                new_pass=NEXT_PHRASE,
                new_pass_check=NEXT_PHRASE,
            )

    def test_verification_mismatch(self):
        with self.assertRaisesRegex(UserError, "verification error"):
            self._change(new_pass=NEXT_PHRASE, new_pass_check=OTHER_PHRASE)

    def test_new_equals_old(self):
        with self.assertRaisesRegex(UserError, "equal to old"):
            self._change(new_pass=INIT_PHRASE, new_pass_check=INIT_PHRASE)

    def test_wrong_old_passphrase_not_stored(self):
        """Without a stored passphrase, fintech rejects the wrong one."""
        self.userid.ebics_passphrase_store = False
        self.userid.ebics_passphrase = False
        with self.assertRaisesRegex(UserError, "(?i)passphrase"):
            self._change(
                old_pass=WRONG_PHRASE,
                new_pass=NEXT_PHRASE,
                new_pass_check=NEXT_PHRASE,
            )

    def test_change_passphrase_not_stored(self):
        """The new passphrase must not be written when storing is off."""
        self.userid.ebics_passphrase_store = False
        self.userid.ebics_passphrase = False
        wizard = self._change(
            old_pass=INIT_PHRASE,
            new_pass=NEXT_PHRASE,
            new_pass_check=NEXT_PHRASE,
        )
        self.assertFalse(self.userid.ebics_passphrase)
        self.assertIn("has been changed", wizard.note)
        keyring = EbicsKeyRing(keys=self.userid.ebics_keys_fn, passphrase=NEXT_PHRASE)
        self.assertTrue(keyring["#USER"])


class FakeAdminClient:
    def __init__(self, error=None):
        self.error = error

    def _order(self, name):
        if self.error:
            raise self.error
        return {"order": name, "Services": [{"ServiceName": "SCT"}]}

    def HAA(self, parsed=False):
        return self._order("HAA")

    def HPD(self, parsed=False):
        return self._order("HPD")

    def HKD(self, parsed=False):
        return self._order("HKD")

    def HTD(self, parsed=False):
        return self._order("HTD")


@tagged("post_install", "-at_install")
class TestAdminOrder(EbicsKeysCommon):
    def _run(self, order_type, client):
        wizard = self.env["ebics.admin.order"].create(
            {
                "ebics_config_id": self.ebics_config.id,
                "ebics_userid_id": self.ebics_userid.id,
                "admin_order_type": order_type,
            }
        )
        wizard_class = type(wizard)
        with patch.object(wizard_class, "_setup_client", return_value=client):
            wizard.ebics_admin_order()
        return wizard

    def test_admin_orders(self):
        for order_type in ("HAA", "HPD", "HKD", "HTD"):
            with self.subTest(order_type=order_type):
                wizard = self._run(order_type, FakeAdminClient())
                expected = pprint.PrettyPrinter().pformat(
                    FakeAdminClient()._order(order_type)
                )
                self.assertEqual(wizard.note, expected)

    def test_admin_order_errors(self):
        cases = [
            (EbicsTechnicalError("061001", "EBICS_AUTHENTICATION_FAILED"), "Technical"),
            (
                EbicsFunctionalError("091005", "EBICS_NO_DOWNLOAD_DATA_AVAILABLE"),
                "Functional",
            ),
        ]
        for error, expected in cases:
            with self.subTest(error=type(error).__name__):
                wizard = self._run("HAA", FakeAdminClient(error=error))
                self.assertIn(
                    f"EBICS {expected} Error during execution of order HAA", wizard.note
                )
                self.assertIn(f"(code: {error.code})", wizard.note)

    def test_admin_order_client_setup_failure(self):
        wizard = self._run("HPD", False)
        self.assertIn("client setup failed", wizard.note)
