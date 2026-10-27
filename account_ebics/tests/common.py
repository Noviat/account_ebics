# Copyright 2026 Noviat.
# License LGPL-3 or later (https://www.gnu.org/licenses/lgpl).

import base64
from contextlib import contextmanager
from unittest.mock import patch

from odoo import Command, fields
from odoo.tools import file_open

from odoo.addons.account.tests.common import AccountTestInvoicingCommon

# Synthetic files: structures mirror real bank files, all values are invented.
SAMPLES_DIR = "account_ebics/tests/samples"

# Bank accounts used in the samples (fictitious, checksum-valid).
IBAN_CMB = "FR7615589297011000000010111"
IBAN_CA833 = [
    "FR7613306000012000000020197",
    "FR7613306000012000000020294",
    "FR7613306000012000000020391",
]
IBAN_LCL = [
    "FR7630002004563000000030102",
    "FR7630002004563000000030296",
    "FR7630002004563000000030393",
    "FR7630002004563000000030490",
]
IBAN_CA879 = [
    "FR7617906000324000000040136",
    "FR7617906000324000000040233",
    "FR7617906000324000000040330",
    "FR7617906000324000000040427",
]
IBAN_CIC = "FR7630087331005000000050175"
IBAN_HVB = "DE54793200750010000001"
IBAN_SPK = "DE52305500000010000002"
IBAN_MULTI = ["DE69370400440010000003", "DE42370400440010000004"]
IBAN_SUFFIX = "DE15370400440010000005"


def read_sample(name):
    with file_open(f"{SAMPLES_DIR}/{name}", "rb") as f:
        return f.read()


class FakeEbicsClient:
    """Stand-in for fintech.ebics.EbicsClient, returned by a patched
    ebics.xfer._setup_client so that no keyring and no bank are needed.

    :param downloads: dict order type ("BTD", "FDL" or the EBICS 2 order
        type) -> bytes (or dict of document name -> bytes) to return.
    :param error: exception instance raised by every transfer call.
    """

    def __init__(self, downloads=None, order_id="N001", error=None):
        self.downloads = downloads or {}
        self.order_id = order_id
        self.error = error
        self.uploads = []
        self.confirmed = []
        self.last_trans_id = "TRANS0001"

    def _download(self, key):
        if self.error:
            raise self.error
        return self.downloads[key]

    def _upload(self, key, data, kwargs):
        if self.error:
            raise self.error
        self.uploads.append((key, data, kwargs))
        return self.order_id

    def BTD(self, btf, start=None, end=None, **kwargs):
        return self._download("BTD")

    def FDL(self, filetype, start=None, end=None):
        return self._download("FDL")

    def download(self, order_type, params=None):
        return self._download(order_type)

    def BTU(self, btf, data, **kwargs):
        return self._upload("BTU", data, kwargs)

    def FUL(self, filetype, data, **kwargs):
        return self._upload("FUL", data, kwargs)

    def upload(self, order_type, data):
        return self._upload(order_type, data, {})

    def confirm_download(self, trans_id=None, success=True):
        self.confirmed.append((trans_id, success))


class EbicsTestCommon(AccountTestInvoicingCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.user.groups_id |= cls.env.ref("account_ebics.group_ebics_manager")
        cls.eur = cls.env.ref("base.EUR")
        cls.eur.active = True
        cls.company = cls.env.company
        cls.ebics_config = cls.env["ebics.config"].create(
            {
                "name": "Test Bank",
                "ebics_host": "TESTHOST",
                "ebics_url": "https://ebics.example.invalid/ebics",
                "ebics_partner": "PARTNER1",
                "ebics_version": "H004",
                "state": "confirm",
            }
        )
        cls.ebics_userid = cls.env["ebics.userid"].create(
            {
                "name": "USER1",
                "ebics_config_id": cls.ebics_config.id,
                "user_ids": [Command.set(cls.env.user.ids)],
                "company_ids": [Command.set(cls.company.ids)],
                "ebics_passphrase": "test-passphrase",
                "ebics_passphrase_store": True,
                "state": "active_keys",
            }
        )
        cls.ff_camt053 = cls.env.ref("account_ebics.ebics_ff_C53")
        cls.ff_cfonb120 = cls.env.ref(
            "account_ebics.ebics_ff_FDL_camt_xxx_cfonb120_stm"
        )
        cls.ff_btd_cfonb120 = cls.env.ref("account_ebics.ebics_ff_btf_cfonb120")

    @classmethod
    def _create_bank_journal(cls, code, acc_number, currency=None):
        # sudo: accountants may not create bank accounts (res.partner.bank)
        journal = (
            cls.env["account.journal"]
            .sudo()
            .create(
                {
                    "name": f"Bank {code}",
                    "code": code,
                    "type": "bank",
                    "bank_acc_number": acc_number,
                    "currency_id": (currency or cls.eur).id,
                    "company_id": cls.company.id,
                }
            )
            .sudo(False)
        )
        cls.ebics_config.journal_ids = [Command.link(journal.id)]
        return journal

    @classmethod
    def _create_ebics_file(cls, sample, file_format, name=None):
        return cls.env["ebics.file"].create(
            {
                "name": name or sample,
                "data": base64.b64encode(read_sample(sample)),
                "date": fields.Datetime.now(),
                "format_id": file_format.id,
            }
        )

    @staticmethod
    def _new_res():
        return {"statement_ids": [], "notifications": []}

    @contextmanager
    def _fake_client(self, client):
        xfer_class = type(self.env["ebics.xfer"])
        with patch.object(xfer_class, "_setup_client", return_value=client):
            yield client

    def _download_wizard(self, file_format, **vals):
        return (
            self.env["ebics.xfer"]
            .with_context(ebics_download=True)
            .create(
                {
                    "ebics_config_id": self.ebics_config.id,
                    "ebics_userid_id": self.ebics_userid.id,
                    "format_id": file_format.id,
                    **vals,
                }
            )
        )

    def _upload_wizard(self, file_format, data=b"<Document/>", fname="pay.xml", **vals):
        return self.env["ebics.xfer"].create(
            {
                "ebics_config_id": self.ebics_config.id,
                "ebics_userid_id": self.ebics_userid.id,
                "format_id": file_format.id,
                "upload_data": base64.b64encode(data),
                "upload_fname": fname,
                **vals,
            }
        )
