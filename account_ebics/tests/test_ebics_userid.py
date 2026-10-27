# Copyright 2026 Noviat.
# License LGPL-3 or later (https://www.gnu.org/licenses/lgpl).

import base64
import gc
import itertools
import os
import shutil
import tempfile
from unittest.mock import patch
from urllib.error import URLError

from fintech.ebics import EbicsFunctionalError, EbicsKeyRing, EbicsTechnicalError

from odoo import Command, fields
from odoo.exceptions import UserError
from odoo.tests import tagged
from odoo.tools import mute_logger

from odoo.addons.account_ebics.models import ebics_userid as ebics_userid_module

from .common import EbicsTestCommon

# Throwaway passphrase for keys created in a temporary directory.
WRONG_PHRASE = "wrong-passphrase"
PUBLIC_BANK_KEYS = (
    "Public bank keys (simulated)\nX002 hash: 00 11 22\nE002 hash: 33 44 55\n"
)


def fake_init_client(hev=None, ini_error=None, hpb_error=None):
    """Return a stand-in for fintech's EbicsClient covering the bank side of
    the key ceremony. Keys, certificates and the INI letter stay real."""

    class FakeInitClient:
        calls = []

        def __init__(self, bank, user, version=None):
            self.bank = bank

        def HEV(self):
            self.calls.append("HEV")
            return hev if hev is not None else {"H004": "2.5", "H005": "3.0"}

        def _order(self, name):
            self.calls.append(name)
            return self.bank._next_order_id("PARTNER1")

        def INI(self):
            if ini_error:
                raise ini_error
            return self._order("INI")

        def HIA(self):
            return self._order("HIA")

        def HPB(self):
            if hpb_error:
                raise hpb_error
            self.calls.append("HPB")
            return PUBLIC_BANK_KEYS

    return FakeInitClient


class EbicsKeysCommon(EbicsTestCommon):
    """Real keys in a temporary directory, simulated bank."""

    _userid_seq = itertools.count(1)

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        keys_dir = tempfile.mkdtemp(prefix="ebics_keys_test_")
        cls.addClassCleanup(shutil.rmtree, keys_dir, ignore_errors=True)
        cls.ebics_config.write({"ebics_keys": keys_dir, "ebics_key_bitlength": 2048})
        cls.bank_fr = cls.env["res.bank"].create(
            {"name": "Banque Test", "country": cls.env.ref("base.fr").id}
        )
        cls.journal = cls._create_bank_journal("TKEY", "FR7630004000031234567890143")
        cls.journal.bank_account_id.sudo().bank_id = cls.bank_fr

    def _new_userid(self, **vals):
        # A new name per test: fintech keeps open keyrings per file in-process.
        return self.env["ebics.userid"].create(
            {
                "name": f"KEYUSER{next(self._userid_seq)}",
                "ebics_config_id": self.ebics_config.id,
                "user_ids": [Command.set(self.env.user.ids)],
                "company_ids": [Command.set(self.company.ids)],
                "ebics_passphrase": "init-passphrase",
                **vals,
            }
        )

    def _init_1(self, userid, client_class=None):
        client_class = client_class or fake_init_client()
        with patch.object(ebics_userid_module, "EbicsClient", client_class):
            userid.ebics_init_1()
        return client_class


@tagged("post_install", "-at_install")
class TestKeyCeremony(EbicsKeysCommon):
    def test_full_ceremony(self):
        userid = self._new_userid(ebics_key_x509=True, ebics_key_x509_dn_cn="Test")
        client_class = self._init_1(userid)
        self.assertEqual(client_class.calls, ["HEV", "INI", "HIA"])
        self.assertEqual(userid.state, "init")
        self.assertTrue(os.path.isfile(userid.ebics_keys_fn))
        self.assertTrue(userid.ebics_keys_found)
        self.assertTrue(base64.b64decode(userid.ebics_ini_letter).startswith(b"%PDF"))
        today = fields.Date.today().isoformat()
        self.assertEqual(userid.ebics_ini_letter_fn, f"TESTHOST_ini_letter_{today}.pdf")

        userid.ebics_init_2()
        self.assertEqual(userid.state, "get_bank_keys")

        with patch.object(ebics_userid_module, "EbicsClient", client_class):
            userid.ebics_init_3()
        self.assertEqual(userid.state, "to_verify")
        self.assertEqual(
            base64.b64decode(userid.ebics_public_bank_keys).decode(), PUBLIC_BANK_KEYS
        )
        self.assertEqual(
            userid.ebics_public_bank_keys_fn, f"TESTHOST_public_bank_keys_{today}.txt"
        )

        bank_class = ebics_userid_module.EbicsBank
        with patch.object(bank_class, "activate_keys") as activate_keys:
            userid.ebics_init_4()
        activate_keys.assert_called_once()
        self.assertEqual(userid.state, "active_keys")
        # stored passphrase is kept
        self.assertEqual(userid.ebics_passphrase, "init-passphrase")

    def test_passphrase_not_stored_is_cleared(self):
        userid = self._new_userid(ebics_passphrase_store=False)
        self._init_1(userid)
        self.assertFalse(userid.ebics_passphrase)

    def test_existing_keys_are_kept(self):
        """A second init reuses the key file: reset tools must delete it."""
        userid = self._new_userid()
        self._init_1(userid)
        with open(userid.ebics_keys_fn, "rb") as f:
            keys = f.read()
        userid.set_to_draft()
        self._init_1(userid)
        with open(userid.ebics_keys_fn, "rb") as f:
            self.assertEqual(f.read(), keys)

    def test_step_guards(self):
        userid = self._new_userid()
        userid.state = "init"
        with self.assertRaisesRegex(UserError, "draft"):
            userid.ebics_init_1()
        userid.state = "draft"
        for method in ("ebics_init_2", "ebics_init_3", "ebics_init_4"):
            with self.subTest(method=method), self.assertRaises(UserError):
                getattr(userid, method)()

    def test_init_requires_passphrase(self):
        userid = self._new_userid(ebics_passphrase=False)
        with self.assertRaisesRegex(UserError, "passphrase"):
            userid.ebics_init_1()

    def test_3skey_requires_certificate(self):
        userid = self._new_userid(swift_3skey=True)
        with self.assertRaisesRegex(UserError, "3SKey certificate"):
            userid.ebics_init_1()

    def test_init_requires_a_journal_with_bank(self):
        self.ebics_config.journal_ids = False
        userid = self._new_userid()
        with self.assertRaisesRegex(UserError, "No bank defined"):
            self._init_1(userid)

    def test_version_not_supported_by_bank(self):
        userid = self._new_userid()
        with self.assertRaisesRegex(UserError, "version mismatch"):
            self._init_1(userid, fake_init_client(hev={"H003": "2.4"}))
        self.assertEqual(userid.state, "draft")

    def test_init_errors(self):
        cases = [
            (URLError("connection refused"), "urlopen error"),
            (
                EbicsFunctionalError("091002", "EBICS_INVALID_USER_OR_USER_STATE"),
                "091002",
            ),
            (EbicsTechnicalError("061001", "EBICS_AUTHENTICATION_FAILED"), "061001"),
        ]
        for error, expected in cases:
            with self.subTest(error=type(error).__name__):
                userid = self._new_userid()
                with (
                    mute_logger(ebics_userid_module.__name__),
                    self.assertRaisesRegex(UserError, expected),
                ):
                    self._init_1(userid, fake_init_client(ini_error=error))

    def test_get_bank_keys_error(self):
        userid = self._new_userid()
        self._init_1(userid)
        userid.ebics_init_2()
        error = EbicsFunctionalError("091002", "EBICS_INVALID_USER_OR_USER_STATE")
        client_class = fake_init_client(hpb_error=error)
        with (
            patch.object(ebics_userid_module, "EbicsClient", client_class),
            self.assertRaisesRegex(UserError, "EBICS Functional Error"),
        ):
            userid.ebics_init_3()

    def test_h003_order_numbers(self):
        self.ebics_config.write({"ebics_version": "H003", "order_number": "A000"})
        userid = self._new_userid()
        self._init_1(userid, fake_init_client(hev={"H003": "2.4"}))
        # INI uses A000, HIA uses A001
        self.assertEqual(self.ebics_config.order_number, "A002")

    def test_ini_letter_language(self):
        calls = []

        class SpyUser(ebics_userid_module.EbicsUser):
            def create_ini_letter(self, bankname, lang=None, **kwargs):
                calls.append((bankname, lang))
                return b"%PDF-1.4 spy"

        cases = [
            ("base.fr", "fr_FR", "fr"),
            ("base.de", "fr_FR", "de"),
            ("base.be", "fr_FR", "fr"),
            ("base.be", "en_US", "en"),
        ]
        for country, user_lang, expected in cases:
            with self.subTest(country=country, user_lang=user_lang):
                lang = (
                    self.env["res.lang"]
                    .sudo()
                    .with_context(active_test=False)
                    .search([("code", "=", user_lang)])
                )
                lang.active = True
                self.bank_fr.country = self.env.ref(country)
                self.env.user.lang = user_lang
                userid = self._new_userid()
                with patch.object(ebics_userid_module, "EbicsUser", SpyUser):
                    self._init_1(userid)
                self.assertEqual(calls[-1], ("Banque Test", expected))

    def test_key_renewal_requires_draft_config(self):
        userid = self._new_userid()
        with self.assertRaisesRegex(UserError, "Key Renewal"):
            userid.set_to_get_bank_keys()
        self.ebics_config.set_to_draft()
        userid.set_to_get_bank_keys()
        self.assertEqual(userid.state, "get_bank_keys")

    def test_h005_requires_x509(self):
        self.ebics_config.ebics_version = "H005"
        with self.assertRaisesRegex(UserError, "X.509"):
            self._new_userid(ebics_key_x509=False)

    def test_stored_passphrase_is_checked(self):
        userid = self._new_userid()
        self._init_1(userid)
        gc.collect()  # no other keyring instance: fintech raises ValueError
        userid.ebics_passphrase = WRONG_PHRASE
        with self.assertRaisesRegex(UserError, "Passphrase mismatch"):
            userid._onchange_ebics_passphrase_store()

    def test_stored_passphrase_is_checked_with_open_keyring(self):
        """In a worker the keyring may already be open with the right
        passphrase: fintech then raises RuntimeError."""
        userid = self._new_userid()
        self._init_1(userid)
        open_keyring = EbicsKeyRing(
            keys=userid.ebics_keys_fn, passphrase=userid.ebics_passphrase
        )
        userid.ebics_passphrase = WRONG_PHRASE
        with self.assertRaisesRegex(UserError, "Passphrase mismatch"):
            userid._onchange_ebics_passphrase_store()
        del open_keyring
