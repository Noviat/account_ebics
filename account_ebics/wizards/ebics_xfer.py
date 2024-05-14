# Copyright 2009-2024 Noviat.
# License LGPL-3 or later (http://www.gnu.org/licenses/lgpl).

import base64
import logging
from sys import exc_info
from traceback import format_exception

from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

try:
    import fintech
    from fintech.ebics import (
        BusinessTransactionFormat,
        EbicsBank,
        EbicsClient,
        EbicsFunctionalError,
        EbicsKeyRing,
        EbicsTechnicalError,
        EbicsUser,
        EbicsVerificationError,
    )

    fintech.cryptolib = "cryptography"
except ImportError:
    EbicsBank = object
    _logger.warning("Failed to import fintech")


class EbicsBank(EbicsBank):
    def _next_order_id(self, partnerid):
        """
        EBICS protocol version H003 requires generation of the OrderID.
        The OrderID must be a string between 'A000' and 'ZZZZ' and
        unique for each partner id.
        """
        return hasattr(self, "_order_number") and self._order_number or "A000"


class EbicsXfer(models.TransientModel):
    _name = "ebics.xfer"
    _description = "EBICS file transfer"

    ebics_config_id = fields.Many2one(
        comodel_name="ebics.config",
        string="EBICS Configuration",
        domain=[("state", "=", "confirm")],
        default=lambda self: self._default_ebics_config_id(),
    )
    ebics_userid_id = fields.Many2one(
        comodel_name="ebics.userid", string="EBICS UserID"
    )
    ebics_passphrase = fields.Char(string="EBICS Passphrase")
    ebics_passphrase_stored = fields.Char(
        string="EBICS Stored Passphrase", related="ebics_userid_id.ebics_passphrase"
    )
    ebics_passphrase_store = fields.Boolean(
        related="ebics_userid_id.ebics_passphrase_store"
    )
    ebics_sig_passphrase = fields.Char(
        string="EBICS Signature Passphrase",
    )
    ebics_sig_passphrase_invisible = fields.Boolean(
        compute="_compute_ebics_sig_passphrase_invisible"
    )
    date_from = fields.Date()
    date_to = fields.Date()
    upload_data = fields.Binary(string="File to Upload")
    upload_fname = fields.Char(string="Upload Filename", default="")
    upload_fname_dummy = fields.Char(
        related="upload_fname", string="Dummy Upload Filename", readonly=True
    )
    format_id = fields.Many2one(
        comodel_name="ebics.file.format",
        string="EBICS File Format",
        help="Select EBICS File Format to upload/download."
        "\nLeave blank to download all available files.",
    )
    upload_format_ids = fields.Many2many(
        comodel_name="ebics.file.format", compute="_compute_upload_format_ids"
    )
    allowed_format_ids = fields.Many2many(
        related="ebics_config_id.ebics_file_format_ids",
        string="Allowed EBICS File Formats",
    )
    order_type = fields.Char(
        related="format_id.order_type",
        string="Order Type",
    )
    test_mode = fields.Boolean(
        help="Select this option to test if the syntax of "
        "the upload file is correct."
        "\nThis option is only available for "
        "Order Type 'FUL'.",
    )
    note = fields.Text(string="EBICS file transfer Log", readonly=True)

    @api.model
    def _default_ebics_config_id(self):
        cfg_mod = self.env["ebics.config"]
        cfg = cfg_mod.search(
            [
                ("company_ids", "in", self.env.user.company_ids.ids),
                ("state", "=", "confirm"),
            ]
        )
        if cfg and len(cfg) == 1:
            return cfg
        else:
            return cfg_mod

    def _compute_ebics_sig_passphrase_invisible(self):
        for rec in self:
            rec.ebics_sig_passphrase_invisible = True
            if fintech.__version_info__ < (7, 3, 1):
                rec.ebics_sig_passphrase_invisible = True
            else:
                rec.ebics_sig_passphrase_invisible = False

    @api.depends("ebics_config_id")
    def _compute_upload_format_ids(self):
        for rec in self:
            rec.upload_format_ids = False
            if not self.env.context.get("ebics_download"):
                rec.upload_format_ids = (
                    rec.ebics_config_id.ebics_file_format_ids.filtered(
                        lambda r: r.type == "up"
                    )
                )

    @api.onchange("ebics_config_id")
    def _onchange_ebics_config_id(self):
        avail_userids = self.ebics_config_id.ebics_userid_ids.filtered(
            lambda r: self.env.user.id in r.user_ids.ids
        )

        if self.env.context.get("ebics_download"):  # Download Form
            avail_formats = self.ebics_config_id.ebics_file_format_ids.filtered(
                lambda r: r.type == "down"
            )
            if avail_formats and len(avail_formats) == 1:
                self.format_id = avail_formats
            else:
                self.format_id = False
            avail_userids = avail_userids.filtered(
                lambda r: r.transaction_rights in ["both", "down"]
            )
        else:  # Upload Form
            if not self.env.context.get("active_model") == "account.payment.order":
                avail_formats = self.ebics_config_id.ebics_file_format_ids.filtered(
                    lambda r: r.type == "up"
                )
                if avail_formats and len(avail_formats) == 1:
                    self.format_id = avail_formats
                else:
                    self.format_id = False
            avail_userids = avail_userids.filtered(
                lambda r: r.transaction_rights in ["both", "up"]
            )

        if avail_userids:
            if len(avail_userids) == 1:
                self.ebics_userid_id = avail_userids
            else:
                with_passphrase_userids = avail_userids.filtered(
                    lambda r: r.ebics_passphrase_store
                )
                if len(with_passphrase_userids) == 1:
                    self.ebics_userid_id = with_passphrase_userids
        else:
            self.ebics_userid_id = False

    @api.onchange("upload_data")
    def _onchange_upload_data(self):
        if self.env.context.get("active_model") == "account.payment.order":
            return
        self.upload_fname_dummy = self.upload_fname
        self.format_id = False
        self._detect_upload_format()
        if not self.format_id:
            upload_formats = (
                self.format_id
                or self.ebics_config_id.ebics_file_format_ids.filtered(
                    lambda r: r.type == "up"
                )
            )
            if len(upload_formats) > 1:
                upload_formats = upload_formats.filtered(
                    lambda r: self.upload_fname.endswith(r.suffix or "")
                )
            if len(upload_formats) == 1:
                self.format_id = upload_formats

    def ebics_upload(self):
        self.ensure_one()
        ctx = self._context.copy()
        ebics_file = self._ebics_upload()
        if ebics_file:
            ctx["ebics_file_id"] = ebics_file.id
        module = __name__.split("addons.")[1].split(".")[0]
        result_view = self.env.ref("%s.ebics_xfer_view_form_result" % module)
        return {
            "name": _("EBICS file transfer result"),
            "res_id": self.id,
            "view_type": "form",
            "view_mode": "form",
            "res_model": "ebics.xfer",
            "view_id": result_view.id,
            "target": "new",
            "context": ctx,
            "type": "ir.actions.act_window",
        }

    def ebics_download(self):
        self.ensure_one()
        ctx = self.env.context.copy()
        self.note = ""
        err_cnt = 0
        client = self._setup_client()
        if not client:
            err_cnt += 1
            self.note += (
                _("EBICS client setup failed for connection '%s'")
                % self.ebics_config_id.name
            )
        else:
            download_formats = (
                self.format_id
                or self.ebics_config_id.ebics_file_format_ids.filtered(
                    lambda r: r.type == "down"
                )
            )
            ebics_files = self.env["ebics.file"]
            date_from = self.date_from and self.date_from.isoformat() or None
            date_to = self.date_to and self.date_to.isoformat() or None
            for df in download_formats:
                try:
                    success = False
                    if df.order_type == "BTD":
                        btf = BusinessTransactionFormat(
                            df.btf_service,
                            df.btf_message,
                            scope=df.btf_scope or None,
                            option=df.btf_option or None,
                            container=df.btf_container or None,
                            version=df.btf_version or None,
                            variant=df.btf_variant or None,
                            format=df.btf_format or None,
                        )
                        data = client.BTD(btf, start=date_from, end=date_to)
                    elif df.order_type == "FDL":
                        data = client.FDL(df.name, date_from, date_to)
                    else:
                        params = None
                        if date_from and date_to:
                            params = {
                                "DateRange": {
                                    "Start": date_from,
                                    "End": date_to,
                                }
                            }
                        data = client.download(df.order_type, params=params)
                    ebics_files += self._handle_download_data(data, df)
                    success = True
                except EbicsFunctionalError:
                    err_cnt += 1
                    e = exc_info()
                    self.note += "\n"
                    self.note += _(
                        "EBICS Functional Error during download of "
                        "File Format %(name)s (%(order_type)s):",
                        name=df.name or df.description,
                        order_type=df.order_type,
                    )
                    self.note += "\n"
                    self.note += "{} (code: {})".format(e[1].message, e[1].code)
                except EbicsTechnicalError:
                    err_cnt += 1
                    e = exc_info()
                    self.note += "\n"
                    self.note += _(
                        "EBICS Technical Error during download of "
                        "File Format %(name)s (%(order_type)s):",
                        name=df.name or df.description,
                        order_type=df.order_type,
                    )
                    self.note += "\n"
                    self.note += "{} (code: {})".format(e[1].message, e[1].code)
                except EbicsVerificationError:
                    err_cnt += 1
                    self.note += "\n"
                    self.note += _(
                        "EBICS Verification Error during download of "
                        "File Format %(name)s (%(order_type)s):",
                        name=df.name or df.description,
                        order_type=df.order_type,
                    )
                    self.note += "\n"
                    self.note += _("The EBICS response could not be verified.")
                except UserError as e:
                    err_cnt += 1
                    self.note += "\n"
                    self.note += _(
                        "Error detected during download of "
                        "File Format %(name)s (%(order_type)s):",
                        name=df.name or df.description,
                        order_type=df.order_type,
                    )
                    self.note += "\n"
                    self.note += " ".join(e.args)
                except Exception:
                    err_cnt += 1
                    self.note += "\n"
                    self.note += _(
                        "Unknown Error during download of "
                        "File Format %(name)s (%(order_type)s):",
                        name=df.name or df.description,
                        order_type=df.order_type,
                    )
                    tb = "".join(format_exception(*exc_info()))
                    self.note += "\n%s" % tb
                else:
                    # mark received data so that it is not included in further
                    # downloads
                    trans_id = client.last_trans_id
                    client.confirm_download(trans_id=trans_id, success=success)

            ctx["ebics_file_ids"] = ebics_files.ids

            if ebics_files:
                self.note += "\n"
                for f in ebics_files:
                    self.note += (
                        _("EBICS File '%s' is available for further processing.")
                        % f.name
                    )
                    self.note += "\n"

        ctx["err_cnt"] = err_cnt
        module = __name__.split("addons.")[1].split(".")[0]
        result_view = self.env.ref("%s.ebics_xfer_view_form_result" % module)
        return {
            "name": _("EBICS file transfer result"),
            "res_id": self.id,
            "view_type": "form",
            "view_mode": "form",
            "res_model": "ebics.xfer",
            "view_id": result_view.id,
            "target": "new",
            "context": ctx,
            "type": "ir.actions.act_window",
        }

    def view_ebics_file(self):
        self.ensure_one()
        module = __name__.split("addons.")[1].split(".")[0]
        act = self.env["ir.actions.act_window"]._for_xml_id(
            "{}.ebics_file_action_download".format(module)
        )
        act["domain"] = [("id", "in", self._context["ebics_file_ids"])]
        return act

    def _ebics_upload(self):
        self.ensure_one()
        ebics_file = self.env["ebics.file"]
        self.note = ""
        client = self._setup_client()
        if client:
            upload_data = base64.decodebytes(self.upload_data)
            ef_format = self.format_id
            OrderID = False
            try:
                order_type = self.order_type
                if order_type == "BTU":
                    btf = BusinessTransactionFormat(
                        ef_format.btf_service,
                        ef_format.btf_message,
                        scope=ef_format.btf_scope or None,
                        option=ef_format.btf_option or None,
                        container=ef_format.btf_container or None,
                        version=ef_format.btf_version or None,
                        variant=ef_format.btf_variant or None,
                        format=ef_format.btf_format or None,
                    )
                    kwargs = {}
                    if self.test_mode:
                        kwargs["TEST"] = "TRUE"
                    OrderID = client.BTU(btf, upload_data, **kwargs)
                elif order_type == "FUL":
                    kwargs = {}
                    bank = self.ebics_config_id.journal_ids[0].bank_id
                    cc = bank.country.code
                    if cc:
                        kwargs["country"] = cc
                    if self.test_mode:
                        kwargs["TEST"] = "TRUE"
                    OrderID = client.FUL(ef_format.name, upload_data, **kwargs)
                else:
                    OrderID = client.upload(order_type, upload_data)
                if OrderID:
                    self.note += "\n"
                    self.note += (
                        _("EBICS File has been uploaded (OrderID %s).") % OrderID
                    )
                    ef_note = _("EBICS OrderID: %s") % OrderID
                    if self.env.context.get("origin"):
                        ef_note += "\n" + _("Origin: %s") % self._context["origin"]
                    suffix = self.format_id.suffix
                    fn = self.upload_fname
                    if suffix and not fn.endswith(suffix):
                        fn = ".".join([fn, suffix])
                    ef_vals = {
                        "name": self.upload_fname,
                        "data": self.upload_data,
                        "date": fields.Datetime.now(),
                        "format_id": self.format_id.id,
                        "state": "done",
                        "user_id": self._uid,
                        "ebics_userid_id": self.ebics_userid_id.id,
                        "note": ef_note,
                        "company_ids": [
                            self.env.context.get("force_company", self.env.company.id)
                        ],
                    }
                    self._update_ef_vals(ef_vals)
                    ebics_file = self.env["ebics.file"].create(ef_vals)

            except EbicsFunctionalError:
                e = exc_info()
                self.note += "\n"
                self.note += _("EBICS Functional Error:")
                self.note += "\n"
                self.note += "{} (code: {})".format(e[1].message, e[1].code)
            except EbicsTechnicalError:
                e = exc_info()
                self.note += "\n"
                self.note += _("EBICS Technical Error:")
                self.note += "\n"
                self.note += "{} (code: {})".format(e[1].message, e[1].code)
            except EbicsVerificationError:
                self.note += "\n"
                self.note += _("EBICS Verification Error:")
                self.note += "\n"
                self.note += _("The EBICS response could not be verified.")
            except Exception:
                self.note += "\n"
                self.note += _("Unknown Error")
                tb = "".join(format_exception(*exc_info()))
                self.note += "\n%s" % tb

            if self.ebics_config_id.ebics_version == "H003":
                OrderID = self.ebics_config_id._get_order_number()
                self.ebics_config_id.sudo()._update_order_number(OrderID)

        ebics_file and self._payment_order_postprocess(ebics_file)
        return ebics_file

    def _payment_order_postprocess(self, ebics_file):
        active_model = self.env.context.get("active_model")
        if active_model == "account.payment.order":
            order = self.env[active_model].browse(self.env.context["active_id"])
            order.generated2uploaded()

    def _setup_client(self):
        self.ebics_config_id._check_ebics_keys()
        passphrase = self._get_passphrase()
        keyring_params = {
            "keys": self.ebics_userid_id.ebics_keys_fn,
            "passphrase": passphrase,
        }
        if self.ebics_sig_passphrase:
            keyring_params["sig_passphrase"] = self.ebics_sig_passphrase
        try:
            keyring = EbicsKeyRing(**keyring_params)
        except (RuntimeError, ValueError) as err:
            error = _("Error while accessing the EBICS Keys:")
            error += "\n"
            error += err.args[0]
            raise UserError(error) from err

        bank = EbicsBank(
            keyring=keyring,
            hostid=self.ebics_config_id.ebics_host,
            url=self.ebics_config_id.ebics_url,
        )
        if self.ebics_config_id.ebics_version == "H003":
            bank._order_number = self.ebics_config_id._get_order_number()

        signature_class = (
            self.format_id.signature_class or self.ebics_userid_id.signature_class
        )

        user_params = {
            "keyring": keyring,
            "partnerid": self.ebics_config_id.ebics_partner,
            "userid": self.ebics_userid_id.name,
        }
        # manual_approval replaced by transport_only class param in fintech 7.4
        fintech74 = hasattr(EbicsUser, "transport_only")
        if fintech74:
            user_params["transport_only"] = signature_class == "T" and True or False
        try:
            user = EbicsUser(**user_params)
        except ValueError as err:
            error = _("Error while accessing the EBICS UserID:")
            error += "\n"
            err_str = err.args[0]
            error += err.args[0]
            if err_str == "unknown key format":
                error += "\n"
                error += _("Doublecheck your EBICS Passphrase and UserID settings.")
            raise UserError(error) from err
        # manual_approval replaced by transport_only class param in fintech 7.4
        if not fintech74 and signature_class == "T":
            user.manual_approval = True

        try:
            client = EbicsClient(bank, user, version=self.ebics_config_id.ebics_version)
        except Exception:
            self.note += "\n"
            self.note += _("Unknown Error")
            tb = "".join(format_exception(*exc_info()))
            self.note += "\n%s" % tb
            client = False

        return client

    def _get_passphrase(self):
        return self.ebics_passphrase or self.ebics_passphrase_stored

    def _file_format_methods(self):
        """
        Extend this dictionary in order to add support
        for extra file formats.
        """
        res = {
            "camt.xxx.cfonb120.stm": self._handle_cfonb120,
            "camt.xxx.cfonb120.stm.rfi": self._handle_cfonb120,
            "camt.052.001.02.stm": self._handle_camt052,
            "camt.053.001.02.stm": self._handle_camt053,
        }
        return res

    def _update_ef_vals(self, ef_vals):
        """
        Adapt this method to customize the EBICS File values.
        """
        if self.format_id and self.format_id.type == "up":
            fn = ef_vals["name"]
            dups = self._check_duplicate_ebics_file(fn, self.format_id)
            if dups:
                n = 1
                fn = "_".join([fn, str(n)])
                while self._check_duplicate_ebics_file(fn, self.format_id):
                    n += 1
                    fn = "_".join([fn, str(n)])
                ef_vals["name"] = fn

    def _handle_download_data(self, data, file_format):
        ebics_files = self.env["ebics.file"]
        if isinstance(data, dict):
            for doc in data:
                ebics_files += self._create_ebics_file(
                    data[doc], file_format, docname=doc
                )
        else:
            ebics_files += self._create_ebics_file(data, file_format)
        return ebics_files

    def _create_ebics_file(self, data, file_format, docname=None):
        fn_parts = [self.ebics_config_id.ebics_host, self.ebics_config_id.ebics_partner]
        if docname:
            fn_parts.append(docname)
        else:
            fn_date = self.date_to or fields.Date.today()
            fn_parts.append(fn_date.isoformat())
        fn = "_".join(fn_parts)
        ff_methods = self._file_format_methods()
        if file_format.name in ff_methods:
            data = ff_methods[file_format.name](data)

        suffix = file_format.suffix
        if suffix and not fn.endswith(suffix):
            fn = ".".join([fn, suffix])
        dups = self._check_duplicate_ebics_file(fn, file_format)
        if dups:
            raise UserError(
                _(
                    "EBICS File with name '%s' has already been downloaded."
                    "\nPlease check this file and rename in case there is "
                    "no risk on duplicate transactions."
                )
                % fn
            )
        data = base64.encodebytes(data)
        ef_vals = {
            "name": fn,
            "data": data,
            "date": fields.Datetime.now(),
            "date_from": self.date_from,
            "date_to": self.date_to,
            "format_id": file_format.id,
            "user_id": self._uid,
            "ebics_userid_id": self.ebics_userid_id.id,
            "company_ids": self.ebics_config_id.company_ids.ids,
        }
        self._update_ef_vals(ef_vals)
        ebics_file = self.env["ebics.file"].create(ef_vals)
        return ebics_file

    def _check_duplicate_ebics_file(self, fn, file_format):
        dups = self.env["ebics.file"].search(
            [("name", "=", fn), ("format_id", "=", file_format.id)]
        )
        return dups

    def _detect_upload_format(self):
        """
        Use this method in order to automatically detect and set the
        EBICS upload file format.
        """

    def _update_order_number(self, OrderID):
        o_list = list(OrderID)
        for i, c in enumerate(reversed(o_list), start=1):
            if c == "9":
                o_list[-i] = "A"
                break
            if c == "Z":
                continue
            else:
                o_list[-i] = chr(ord(c) + 1)
                break
        next_nr = "".join(o_list)
        if next_nr == "ZZZZ":
            next_nr = "A000"
        self.ebics_config_id.order_number = next_nr

    def _insert_line_terminator(self, data_in, line_len):
        data_in = data_in.replace(b"\n", b"").replace(b"\r", b"")
        data_out = b""
        max_len = len(data_in)
        i = 0
        while i + line_len <= max_len:
            data_out += data_in[i : i + line_len] + b"\n"
            i += line_len
        return data_out

    def _handle_cfonb120(self, data_in):
        return self._insert_line_terminator(data_in, 120)

    def _handle_cfonb240(self, data_in):
        return self._insert_line_terminator(data_in, 240)

    def _handle_camt052(self, data_in):
        """
        Use this method if you need to fix camt files received
        from your bank before passing them to the
        Odoo Community CAMT parser.
        Remark: Odoo Enterprise doesn't support camt.052.
        """
        return data_in

    def _handle_camt053(self, data_in):
        """
        Use this method if you need to fix camt files received
        from your bank before passing them to the
        Odoo Enterprise or Community CAMT parser.
        """
        return data_in
