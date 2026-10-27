# Copyright 2026 Noviat.
# License LGPL-3 or later (https://www.gnu.org/licenses/lgpl).

import base64
from datetime import date

from fintech.ebics import (
    EbicsFunctionalError,
    EbicsTechnicalError,
    EbicsVerificationError,
)

from odoo.tests import tagged

from .common import EbicsTestCommon, FakeEbicsClient, read_sample


@tagged("post_install", "-at_install")
class TestEbicsXferDownload(EbicsTestCommon):
    def test_line_terminator(self):
        xfer = self.env["ebics.xfer"]
        line_a, line_b = b"A" * 120, b"B" * 120
        self.assertEqual(
            xfer._handle_cfonb120(line_a + line_b), line_a + b"\n" + line_b + b"\n"
        )
        self.assertEqual(
            xfer._handle_cfonb120(line_a + b"\r\n" + line_b + b"\r\n"),
            line_a + b"\n" + line_b + b"\n",
        )
        self.assertEqual(
            xfer._handle_cfonb240(line_a + line_b), line_a + line_b + b"\n"
        )
        # Current behaviour: an incomplete trailing line is dropped.
        self.assertEqual(xfer._handle_cfonb120(line_a + b"C" * 10), line_a + b"\n")

    def test_download_fdl_cfonb(self):
        data = read_sample("cfonb120_no_eol_single_account.dat")
        wizard = self._download_wizard(self.ff_cfonb120, date_to=date(2026, 10, 13))
        with self._fake_client(FakeEbicsClient(downloads={"FDL": data})) as client:
            action = wizard.ebics_download()
        self.assertEqual(action["context"]["err_cnt"], 0)
        ebics_file = self.env["ebics.file"].browse(action["context"]["ebics_file_ids"])
        self.assertEqual(ebics_file.name, "TESTHOST_PARTNER1_2026-10-13.cfonb120.dat")
        self.assertEqual(ebics_file.state, "draft")
        self.assertEqual(ebics_file.ebics_userid_id, self.ebics_userid)
        self.assertEqual(ebics_file.company_ids, self.ebics_config.company_ids)
        # FDL CFONB downloads get a line terminator every 120 characters
        stored = base64.b64decode(ebics_file.data)
        self.assertEqual(stored.count(b"\n"), 7)
        self.assertEqual(client.confirmed, [("TRANS0001", True)])
        self.assertIn("is available for further processing", wizard.note)

    def test_download_btd_cfonb(self):
        data = read_sample("cfonb120_no_eol_single_account.dat")
        wizard = self._download_wizard(self.ff_btd_cfonb120, date_to=date(2026, 10, 13))
        with self._fake_client(FakeEbicsClient(downloads={"BTD": data})):
            action = wizard.ebics_download()
        ebics_file = self.env["ebics.file"].browse(action["context"]["ebics_file_ids"])
        self.assertEqual(len(ebics_file), 1)
        # BTD formats have no name, hence no line terminator handler.
        self.assertEqual(base64.b64decode(ebics_file.data), data)

    def test_same_name_in_another_format(self):
        """FDL and BTD CFONB formats share the file suffix: same file name,
        but a different format is not a duplicate."""
        data = read_sample("cfonb120_no_eol_single_account.dat")
        names = []
        for file_format, order_type in (
            (self.ff_cfonb120, "FDL"),
            (self.ff_btd_cfonb120, "BTD"),
        ):
            wizard = self._download_wizard(file_format, date_to=date(2026, 10, 13))
            client = FakeEbicsClient(downloads={order_type: data})
            with self._fake_client(client):
                action = wizard.ebics_download()
            self.assertEqual(action["context"]["err_cnt"], 0)
            ebics_file = self.env["ebics.file"].browse(
                action["context"]["ebics_file_ids"]
            )
            names.append(ebics_file.name)
        self.assertEqual(names[0], names[1])

    def test_download_same_file_twice(self):
        data = read_sample("cfonb120_no_eol_single_account.dat")
        for expected_errors in (0, 1):
            wizard = self._download_wizard(self.ff_cfonb120, date_to=date(2026, 10, 13))
            with self._fake_client(FakeEbicsClient(downloads={"FDL": data})) as client:
                action = wizard.ebics_download()
            self.assertEqual(action["context"]["err_cnt"], expected_errors)
        self.assertIn("has already been downloaded", wizard.note)
        self.assertEqual(client.confirmed, [("TRANS0001", False)])

    def test_download_several_documents(self):
        ptk = self.env["ebics.file.format"].create(
            {"name": "PTK", "type": "down", "order_type": "PTK", "suffix": "txt"}
        )
        data = read_sample("ptk_protocol.txt")
        wizard = self._download_wizard(ptk)
        client = FakeEbicsClient(downloads={"PTK": {"doc1": data, "doc2": data}})
        with self._fake_client(client):
            action = wizard.ebics_download()
        ebics_files = self.env["ebics.file"].browse(action["context"]["ebics_file_ids"])
        self.assertEqual(
            sorted(ebics_files.mapped("name")),
            ["TESTHOST_PARTNER1_doc1.txt", "TESTHOST_PARTNER1_doc2.txt"],
        )
        # no processing method: the files are done right away
        self.assertEqual(set(ebics_files.mapped("state")), {"done"})

    def test_mark_as_downloaded(self):
        data = read_sample("cfonb120_no_eol_single_account.dat")
        wizard = self._download_wizard(self.ff_cfonb120).with_context(
            ebics_mark_as_downloaded=True
        )
        with self._fake_client(FakeEbicsClient(downloads={"FDL": data})) as client:
            action = wizard.ebics_download()
        self.assertFalse(action["context"]["ebics_file_ids"])
        self.assertEqual(client.confirmed, [("TRANS0001", True)])

    def test_download_errors(self):
        cases = [
            (
                EbicsFunctionalError("091005", "EBICS_NO_DOWNLOAD_DATA_AVAILABLE"),
                "EBICS Functional Error",
                "EBICS_NO_DOWNLOAD_DATA_AVAILABLE (code: 091005)",
            ),
            (
                EbicsTechnicalError("061002", "EBICS_INVALID_REQUEST"),
                "EBICS Technical Error",
                "EBICS_INVALID_REQUEST (code: 061002)",
            ),
            (
                EbicsVerificationError(),
                "EBICS Verification Error",
                "could not be verified",
            ),
            (RuntimeError("socket closed"), "Unknown Error", "socket closed"),
        ]
        for error, title, detail in cases:
            with self.subTest(error=type(error).__name__):
                wizard = self._download_wizard(self.ff_cfonb120)
                with self._fake_client(FakeEbicsClient(error=error)) as client:
                    action = wizard.ebics_download()
                self.assertEqual(action["context"]["err_cnt"], 1)
                self.assertFalse(action["context"]["ebics_file_ids"])
                self.assertIn(title, wizard.note)
                self.assertIn(detail, wizard.note)
                self.assertEqual(client.confirmed, [("TRANS0001", False)])

    def test_client_setup_failure(self):
        wizard = self._download_wizard(self.ff_cfonb120)
        with self._fake_client(False):
            action = wizard.ebics_download()
        self.assertEqual(action["context"]["err_cnt"], 1)
        self.assertIn("client setup failed", wizard.note)


@tagged("post_install", "-at_install")
class TestEbicsXferUpload(EbicsTestCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.ff_btu = cls.env["ebics.file.format"].create(
            {
                "type": "up",
                "order_type": "BTU",
                "btf_service": "SCT",
                "btf_message": "pain.001",
                "suffix": "xml",
            }
        )
        cls.ff_ful = cls.env.ref("account_ebics.ebics_ff_LCR")
        bank = cls.env["res.bank"].create(
            {"name": "Test Bank FR", "country": cls.env.ref("base.fr").id}
        )
        journal = cls._create_bank_journal("TUPL", "FR7630004000031234567890143")
        journal.bank_account_id.sudo().bank_id = bank

    def test_upload_btu(self):
        wizard = self._upload_wizard(self.ff_btu, test_mode=True)
        with self._fake_client(FakeEbicsClient(order_id="N042")) as client:
            ebics_file = wizard._ebics_upload()
        self.assertEqual(ebics_file.name, "pay.xml")
        self.assertEqual(ebics_file.state, "done")
        self.assertEqual(ebics_file.pain_state, "uploaded")
        self.assertEqual(ebics_file.ebics_order_number, "N042")
        self.assertEqual(client.uploads, [("BTU", b"<Document/>", {"TEST": "TRUE"})])
        self.assertIn("OrderID N042", wizard.note)
        # H004: the order number is managed by the bank
        self.assertFalse(self.ebics_config.order_number)

    def test_upload_same_name_twice(self):
        """The counter goes before the extension and does not stack up."""
        names = []
        for _i in range(4):
            wizard = self._upload_wizard(self.ff_btu)
            with self._fake_client(FakeEbicsClient()):
                names.append(wizard._ebics_upload().name)
        self.assertEqual(names, ["pay.xml", "pay_1.xml", "pay_2.xml", "pay_3.xml"])
        # without extension
        wizard = self._upload_wizard(self.ff_btu, fname="pay")
        with self._fake_client(FakeEbicsClient()):
            self.assertEqual(wizard._ebics_upload().name, "pay")
        wizard = self._upload_wizard(self.ff_btu, fname="pay")
        with self._fake_client(FakeEbicsClient()):
            self.assertEqual(wizard._ebics_upload().name, "pay_1")

    def test_upload_ful_h003_order_number(self):
        self.ebics_config.write({"ebics_version": "H003", "order_number": "A00Z"})
        wizard = self._upload_wizard(self.ff_ful, fname="lcr.txt")
        with self._fake_client(FakeEbicsClient(order_id="A00Z")) as client:
            ebics_file = wizard._ebics_upload()
        self.assertEqual(ebics_file.ebics_order_number, "A00Z")
        self.assertEqual(client.uploads[0][0], "FUL")
        self.assertEqual(client.uploads[0][2], {"country": "FR"})
        self.assertEqual(self.ebics_config.order_number, "A010")

    def test_upload_h003_failure_still_increments(self):
        """Pinned behaviour: the order number moves on even if the upload failed."""
        self.ebics_config.write({"ebics_version": "H003", "order_number": "B000"})
        wizard = self._upload_wizard(self.ff_ful, fname="lcr.txt")
        error = EbicsFunctionalError("091112", "EBICS_INVALID_ORDER_PARAMS")
        with self._fake_client(FakeEbicsClient(error=error)):
            ebics_file = wizard._ebics_upload()
        self.assertFalse(ebics_file)
        self.assertEqual(self.ebics_config.order_number, "B001")
        self.assertIn("EBICS Functional Error", wizard.note)
        self.assertIn("EBICS_INVALID_ORDER_PARAMS (code: 091112)", wizard.note)

    def test_upload_errors(self):
        cases = [
            (EbicsTechnicalError("061001", "EBICS_AUTHENTICATION_FAILED"), "Technical"),
            (EbicsVerificationError(), "Verification"),
            (RuntimeError("socket closed"), "Unknown Error"),
        ]
        for error, expected in cases:
            with self.subTest(error=type(error).__name__):
                wizard = self._upload_wizard(self.ff_btu)
                with self._fake_client(FakeEbicsClient(error=error)):
                    self.assertFalse(wizard._ebics_upload())
                self.assertIn(expected, wizard.note)

    def test_upload_onchange_selects_format(self):
        """A single upload format on the config is selected automatically."""
        self.ebics_config.ebics_file_format_ids = self.ff_btu
        wizard = self.env["ebics.xfer"].new(
            {"ebics_config_id": self.ebics_config.id, "upload_fname": "pay.xml"}
        )
        wizard._onchange_ebics_config_id()
        self.assertEqual(wizard.format_id, self.ff_btu)
        self.assertEqual(wizard.ebics_userid_id, self.ebics_userid)
