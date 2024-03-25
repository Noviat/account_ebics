# Copyright 2009-2024 Noviat.
# License LGPL-3 or later (http://www.gnu.org/licenses/lgpl).

import base64
import logging
import os
from sys import exc_info
from traceback import format_exception
from urllib.error import URLError

from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

try:
    import fintech
    from fintech.ebics import (
        EbicsBank,
        EbicsClient,
        EbicsFunctionalError,
        EbicsKeyRing,
        EbicsTechnicalError,
        EbicsUser,
    )

    fintech.cryptolib = "cryptography"
except ImportError:
    _logger.warning("Failed to import fintech")


class EbicsBank(EbicsBank):
    def _next_order_id(self, partnerid):
        """
        EBICS protocol version H003 requires generation of the OrderID.
        The OrderID must be a string between 'A000' and 'ZZZZ' and
        unique for each partner id.
        """
        return hasattr(self, "_order_number") and self._order_number or "A000"


class EbicsUserID(models.Model):
    _name = "ebics.userid"
    _description = "EBICS UserID"
    _order = "name"

    name = fields.Char(
        string="EBICS UserID",
        required=True,
        readonly=True,
        states={"draft": [("readonly", False)]},
        help="Human users or a technical system that is/are "
        "assigned to a customer. "
        "\nOn the EBICS bank server it is identified "
        "by the combination of UserID and PartnerID. "
        "The technical subscriber serves only for the data exchange "
        "between customer and financial institution. "
        "The human user also can authorise orders.",
    )
    ebics_config_id = fields.Many2one(
        comodel_name="ebics.config",
        string="EBICS Configuration",
        ondelete="cascade",
        required=True,
    )
    ebics_version = fields.Selection(related="ebics_config_id.ebics_version")
    user_ids = fields.Many2many(
        comodel_name="res.users",
        string="Users",
        required=True,
        help="Users who are allowed to use this EBICS UserID for "
        " bank transactions.",
    )
    # Currently only a single signature class per user is supported
    # Classes A and B are not yet supported.
    signature_class = fields.Selection(
        selection=[("E", "Single signature"), ("T", "Transport signature")],
        required=True,
        default="T",
        readonly=True,
        states={"draft": [("readonly", False)]},
        help="Default signature class."
        "This default can be overriden for specific "
        "EBICS transactions (cf. File Formats).",
    )
    transaction_rights = fields.Selection(
        selection=[
            ("both", "Download and Upload"),
            ("down", "Download Only"),
            ("up", "Upload Only"),
        ],
        string="Allowed Transactions",
        default="both",
        required=True,
        help="Use this parameter to limit the transactions for this User "
        "to downloads or uploads.",
    )
    ebics_keys_fn = fields.Char(compute="_compute_ebics_keys_fn")
    ebics_keys_found = fields.Boolean(compute="_compute_ebics_keys_found")
    ebics_passphrase = fields.Char(string="EBICS Passphrase")
    ebics_passphrase_store = fields.Boolean(
        string="Store EBICS Passphrase",
        default=True,
        help="When you uncheck this option the passphrase to unlock "
        "your private key will not be stored in the database. "
        "We recommend to use this if you want to upload signed "
        "payment orders via EBICS.\nYou will be prompted to enter the "
        "passphrase for every EBICS transaction, hence do not uncheck this "
        "option on a userid for automated EBICS downloads.",
    )
    ebics_passphrase_required = fields.Boolean(
        compute="_compute_ebics_passphrase_view_modifiers"
    )
    ebics_passphrase_invisible = fields.Boolean(
        compute="_compute_ebics_passphrase_view_modifiers"
    )
    ebics_passphrase_store_readonly = fields.Boolean(
        compute="_compute_ebics_passphrase_view_modifiers"
    )
    ebics_sig_passphrase = fields.Char(
        string="EBICS Signature Passphrase",
        help="You can set here a different passphrase for the EBICS "
        "signing key. This passphrase will never be stored hence "
        "you'll need to specify your passphrase for each transaction that "
        "requires a digital signature.",
    )
    ebics_sig_passphrase_invisible = fields.Boolean(
        compute="_compute_ebics_sig_passphrase_invisible"
    )
    ebics_ini_letter = fields.Binary(
        string="EBICS INI Letter",
        readonly=True,
        help="INI-letter PDF document to be sent to your bank.",
    )
    ebics_ini_letter_fn = fields.Char(string="INI-letter Filename", readonly=True)
    ebics_public_bank_keys = fields.Binary(
        string="EBICS Public Bank Keys",
        readonly=True,
        help="EBICS Public Bank Keys to be checked for consistency.",
    )
    ebics_public_bank_keys_fn = fields.Char(
        string="EBICS Public Bank Keys Filename", readonly=True
    )
    swift_3skey = fields.Boolean(
        string="Enable 3SKey support",
        help="Transactions for this user will be signed "
        "by means of the SWIFT 3SKey token.",
    )
    swift_3skey_certificate = fields.Binary(string="3SKey Certficate")
    swift_3skey_certificate_fn = fields.Char(string="3SKey Certificate Filename")
    # X.509 Distinguished Name attributes used to
    # create self-signed X.509 certificates
    ebics_key_x509 = fields.Boolean(
        string="X509 support",
        readonly=True,
        states={"draft": [("readonly", False)]},
        help="Set this flag in order to work with " "self-signed X.509 certificates",
    )
    ebics_key_x509_dn_cn = fields.Char(
        string="Common Name [CN]",
        readonly=True,
        states={"draft": [("readonly", False)]},
    )
    ebics_key_x509_dn_o = fields.Char(
        string="Organization Name [O]",
        readonly=True,
        states={"draft": [("readonly", False)]},
    )
    ebics_key_x509_dn_ou = fields.Char(
        string="Organizational Unit Name [OU]",
        readonly=True,
        states={"draft": [("readonly", False)]},
    )
    ebics_key_x509_dn_c = fields.Char(
        string="Country Name [C]",
        readonly=True,
        states={"draft": [("readonly", False)]},
    )
    ebics_key_x509_dn_st = fields.Char(
        string="State Or Province Name [ST]",
        readonly=True,
        states={"draft": [("readonly", False)]},
    )
    ebics_key_x509_dn_l = fields.Char(
        string="Locality Name [L]",
        readonly=True,
        states={"draft": [("readonly", False)]},
    )
    ebics_key_x509_dn_e = fields.Char(
        string="Email Address",
        readonly=True,
        states={"draft": [("readonly", False)]},
    )
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("init", "Initialisation"),
            ("get_bank_keys", "Get Keys from Bank"),
            ("to_verify", "Verification"),
            ("active_keys", "Active Keys"),
        ],
        default="draft",
        required=True,
        readonly=True,
    )
    active = fields.Boolean(default=True)
    company_ids = fields.Many2many(
        comodel_name="res.company",
        string="Companies",
        required=True,
        help="Companies sharing this EBICS contract.",
    )

    @api.depends("name", "ebics_config_id.ebics_keys")
    def _compute_ebics_keys_fn(self):
        for rec in self:
            keys_dir = rec.ebics_config_id.ebics_keys
            rec.ebics_keys_fn = (
                rec.name
                and keys_dir
                and (keys_dir + "/" + rec.name.replace(" ", "_") + "_keys")
            )

    @api.depends("ebics_keys_fn")
    def _compute_ebics_keys_found(self):
        for rec in self:
            rec.ebics_keys_found = rec.ebics_keys_fn and os.path.isfile(
                rec.ebics_keys_fn
            )

    @api.depends("state", "ebics_passphrase", "ebics_keys_found")
    def _compute_ebics_passphrase_view_modifiers(self):
        for rec in self:
            rec.ebics_passphrase_required = False
            rec.ebics_passphrase_invisible = True
            rec.ebics_passphrase_store_readonly = True
            if rec.state == "draft":
                rec.ebics_passphrase_required = True
                rec.ebics_passphrase_invisible = rec.ebics_keys_found and True or False
                rec.ebics_passphrase_store_readonly = False
            elif rec.state == "init":
                rec.ebics_passphrase_required = False
                rec.ebics_passphrase_invisible = True
            elif rec.state in ("get_bank_keys", "to_verify"):
                rec.ebics_passphrase_required = not rec.ebics_passphrase
                rec.ebics_passphrase_invisible = rec.ebics_passphrase

    @api.depends("state")
    def _compute_ebics_sig_passphrase_invisible(self):
        for rec in self:
            rec.ebics_sig_passphrase_invisible = True
            if fintech.__version_info__ < (7, 3, 1):
                continue
            if rec.transaction_rights != "down" and rec.state == "draft":
                rec.ebics_sig_passphrase_invisible = False

    @api.constrains("ebics_key_x509")
    def _check_ebics_key_x509(self):
        for cfg in self:
            if cfg.ebics_version == "H005" and not cfg.ebics_key_x509:
                raise UserError(_("X.509 certificates must be used with EBICS 3.0."))

    @api.constrains("ebics_passphrase")
    def _check_ebics_passphrase(self):
        for rec in self:
            if rec.ebics_passphrase and len(rec.ebics_passphrase) < 8:
                raise UserError(_("The Passphrase must be at least 8 characters long"))

    @api.constrains("ebics_sig_passphrase")
    def _check_ebics_sig_passphrase(self):
        for rec in self:
            if rec.ebics_sig_passphrase and len(rec.ebics_sig_passphrase) < 8:
                raise UserError(
                    _("The Signature Passphrase must be at least 8 characters long")
                )

    @api.onchange("ebics_version")
    def _onchange_ebics_version(self):
        if self.ebics_version == "H005":
            self.ebics_key_x509 = True

    @api.onchange("signature_class")
    def _onchange_signature_class(self):
        if self.signature_class == "T":
            self.swift_3skey = False

    @api.onchange("ebics_passphrase_store", "ebics_passphrase")
    def _onchange_ebics_passphrase_store(self):
        if self.ebics_passphrase_store:
            if self.ebics_passphrase:
                # check passphrase before db store
                keyring_params = {
                    "keys": self.ebics_keys_fn,
                    "passphrase": self.ebics_passphrase,
                }
                keyring = EbicsKeyRing(**keyring_params)
                try:
                    # fintech <= 7.4.3 does not have a call to check if a
                    # passphrase matches with the value stored in the keyfile.
                    # We get around this limitation as follows:
                    # Get user keys to check for valid passphrases
                    # It will raise a ValueError on invalid passphrases
                    keyring["#USER"]
                except ValueError as err:  # noqa: F841
                    raise UserError(_("Passphrase mismatch."))  # noqa: B904
        else:
            if self.state != "draft":
                self.ebics_passphrase = False

    @api.onchange("swift_3skey")
    def _onchange_swift_3skey(self):
        if self.swift_3skey:
            self.ebics_key_x509 = True

    def set_to_draft(self):
        return self.write({"state": "draft"})

    def set_to_active_keys(self):
        vals = {"state": "active_keys"}
        self._update_passphrase_vals(vals)
        return self.write(vals)

    def set_to_get_bank_keys(self):
        self.ensure_one()
        if self.ebics_config_id.state != "draft":
            raise UserError(
                _(
                    "Set the EBICS Configuation record to 'Draft' "
                    "before starting the Key Renewal process."
                )
            )
        return self.write({"state": "get_bank_keys"})

    def ebics_init_1(self):  # noqa: C901
        """
        Initialization of bank keys - Step 1:
        Create new keys and certificates for this user
        """
        self.ensure_one()
        if self.state != "draft":
            raise UserError(
                _("Set state to 'draft' before Bank Key (re)initialisation.")
            )

        if not self.ebics_passphrase:
            raise UserError(_("Set a passphrase."))

        if self.swift_3skey and not self.swift_3skey_certificate:
            raise UserError(_("3SKey certificate missing."))

        ebics_version = self.ebics_config_id.ebics_version
        try:
            keyring_params = {
                "keys": self.ebics_keys_fn,
                "passphrase": self.ebics_passphrase,
            }
            if self.ebics_sig_passphrase:
                keyring_params["sig_passphrase"] = self.ebics_sig_passphrase
            keyring = EbicsKeyRing(**keyring_params)
            bank = EbicsBank(
                keyring=keyring,
                hostid=self.ebics_config_id.ebics_host,
                url=self.ebics_config_id.ebics_url,
            )
            user = EbicsUser(
                keyring=keyring,
                partnerid=self.ebics_config_id.ebics_partner,
                userid=self.name,
            )
        except Exception as err:
            exctype, value = exc_info()[:2]
            error = _("EBICS Initialisation Error:")
            error += "\n" + str(exctype) + "\n" + str(value)
            raise UserError(error) from err

        self.ebics_config_id._check_ebics_keys()
        if not os.path.isfile(self.ebics_keys_fn):
            try:
                # TODO:
                # enable import of all type of certicates: A00x, X002, E002
                if self.swift_3skey:
                    kwargs = {
                        self.ebics_config_id.ebics_key_version: base64.decodebytes(
                            self.swift_3skey_certificate
                        ),
                    }
                    user.import_certificates(**kwargs)
                user.create_keys(
                    keyversion=self.ebics_config_id.ebics_key_version,
                    bitlength=self.ebics_config_id.ebics_key_bitlength,
                )
            except Exception as err:
                exctype, value = exc_info()[:2]
                error = _("EBICS Initialisation Error:")
                error += "\n" + str(exctype) + "\n" + str(value)
                raise UserError(error) from err

        if self.swift_3skey and not self.ebics_key_x509:
            raise UserError(
                _(
                    "The current version of this module "
                    "requires to X509 support when enabling 3SKey"
                )
            )

        if self.ebics_key_x509:
            dn_attrs = {
                "commonName": self.ebics_key_x509_dn_cn,
                "organizationName": self.ebics_key_x509_dn_o,
                "organizationalUnitName": self.ebics_key_x509_dn_ou,
                "countryName": self.ebics_key_x509_dn_c,
                "stateOrProvinceName": self.ebics_key_x509_dn_st,
                "localityName": self.ebics_key_x509_dn_l,
                "emailAddress": self.ebics_key_x509_dn_e,
            }
            kwargs = {k: v for k, v in dn_attrs.items() if v}
            user.create_certificates(**kwargs)

        try:
            client = EbicsClient(bank, user, version=ebics_version)
        except RuntimeError as err:
            e = exc_info()
            error = _("EBICS Initialization Error:")
            error += "\n"
            error += err.args[0]
            raise UserError(error) from err

        # Send the public electronic signature key to the bank.
        ebics_config_bank = self.ebics_config_id.journal_ids[0].bank_id
        if not ebics_config_bank:
            raise UserError(
                _("No bank defined for the financial journal " "of the EBICS Config")
            )
        try:
            supported_versions = client.HEV()
            if supported_versions and ebics_version not in supported_versions:
                err_msg = _("EBICS version mismatch.") + "\n"
                err_msg += _("Versions supported by your bank:")
                for k in supported_versions:
                    err_msg += "\n{}: {} ".format(k, supported_versions[k])
                raise UserError(err_msg)
            if ebics_version == "H003":
                bank._order_number = self.ebics_config_id._get_order_number()
            OrderID = client.INI()
            _logger.info("%s, EBICS INI command, OrderID=%s", self._name, OrderID)
            if ebics_version == "H003":
                self.ebics_config_id._update_order_number(OrderID)
        except URLError as err:
            exctype, value = exc_info()[:2]
            tb = "".join(format_exception(*exc_info()))
            _logger.error(
                "EBICS INI command error\nUserID: %s\n%s",
                self.name,
                tb,
            )
            raise UserError(
                _(
                    "urlopen error:\n url '%(url)s' - %(val)s",
                    url=self.ebics_config_id.ebics_url,
                    val=str(value),
                )
            ) from err
        except EbicsFunctionalError as err:
            e = exc_info()
            error = _("EBICS Functional Error:")
            error += "\n"
            error += "{} (code: {})".format(e[1].message, e[1].code)
            raise UserError(error) from err
        except EbicsTechnicalError as err:
            e = exc_info()
            error = _("EBICS Technical Error:")
            error += "\n"
            error += "{} (code: {})".format(e[1].message, e[1].code)
            raise UserError(error) from err

        # Send the public authentication and encryption keys to the bank.
        if ebics_version == "H003":
            bank._order_number = self.ebics_config_id._get_order_number()
        OrderID = client.HIA()
        _logger.info("%s, EBICS HIA command, OrderID=%s", self._name, OrderID)
        if ebics_version == "H003":
            self.ebics_config_id._update_order_number(OrderID)

        # Create an INI-letter which must be printed and sent to the bank.
        ebics_config_bank = self.ebics_config_id.journal_ids[0].bank_id
        cc = ebics_config_bank.country.code
        if cc in ["FR", "DE"]:
            lang = cc
        else:
            lang = self.env.user.lang or self.env["res.lang"].search([])[0].code
            lang = lang[:2]
        fn_date = fields.Date.today().isoformat()
        fn = "_".join([self.ebics_config_id.ebics_host, "ini_letter", fn_date]) + ".pdf"
        letter = user.create_ini_letter(bankname=ebics_config_bank.name, lang=lang)
        vals = {
            "ebics_ini_letter": base64.encodebytes(letter),
            "ebics_ini_letter_fn": fn,
            "state": "init",
        }
        self._update_passphrase_vals(vals)
        return self.write(vals)

    def ebics_init_2(self):
        """
        Initialization of bank keys - Step 2:
        Activation of the account by the bank.
        """
        self.ensure_one()
        if self.state != "init":
            raise UserError(_("Set state to 'Initialisation'."))
        vals = {"state": "get_bank_keys"}
        self._update_passphrase_vals(vals)
        return self.write(vals)

    def ebics_init_3(self):
        """
        Initialization of bank keys - Step 3:

        After the account has been activated the public bank keys
        must be downloaded and checked for consistency.
        """
        self.ensure_one()
        if self.state != "get_bank_keys":
            raise UserError(_("Set state to 'Get Keys from Bank'."))
        try:
            keyring = EbicsKeyRing(
                keys=self.ebics_keys_fn, passphrase=self.ebics_passphrase
            )
            bank = EbicsBank(
                keyring=keyring,
                hostid=self.ebics_config_id.ebics_host,
                url=self.ebics_config_id.ebics_url,
            )
            user = EbicsUser(
                keyring=keyring,
                partnerid=self.ebics_config_id.ebics_partner,
                userid=self.name,
            )
            client = EbicsClient(bank, user, version=self.ebics_config_id.ebics_version)
        except Exception as err:
            exctype, value = exc_info()[:2]
            error = _("EBICS Initialisation Error:")
            error += "\n" + str(exctype) + "\n" + str(value)
            raise UserError(error) from err

        try:
            public_bank_keys = client.HPB()
        except EbicsFunctionalError as err:
            e = exc_info()
            error = _("EBICS Functional Error:")
            error += "\n"
            error += "{} (code: {})".format(e[1].message, e[1].code)
            raise UserError(error) from err
        except Exception as err:
            exctype, value = exc_info()[:2]
            error = _("EBICS Initialisation Error:")
            error += "\n" + str(exctype) + "\n" + str(value)
            raise UserError(error) from err

        public_bank_keys = public_bank_keys.encode()
        fn_date = fields.Date.today().isoformat()
        fn = (
            "_".join([self.ebics_config_id.ebics_host, "public_bank_keys", fn_date])
            + ".txt"
        )
        vals = {
            "ebics_public_bank_keys": base64.encodebytes(public_bank_keys),
            "ebics_public_bank_keys_fn": fn,
            "state": "to_verify",
        }
        self._update_passphrase_vals(vals)
        return self.write(vals)

    def ebics_init_4(self):
        """
        Initialization of bank keys - Step 2:
        Confirm Verification of the public bank keys
        and activate the bank keys.
        """
        self.ensure_one()
        if self.state != "to_verify":
            raise UserError(_("Set state to 'Verification'."))

        keyring = EbicsKeyRing(
            keys=self.ebics_keys_fn, passphrase=self.ebics_passphrase
        )
        bank = EbicsBank(
            keyring=keyring,
            hostid=self.ebics_config_id.ebics_host,
            url=self.ebics_config_id.ebics_url,
        )
        bank.activate_keys()
        vals = {"state": "active_keys"}
        self._update_passphrase_vals(vals)
        return self.write(vals)

    def change_passphrase(self):
        self.ensure_one()
        ctx = dict(self.env.context, default_ebics_userid_id=self.id)
        module = __name__.split("addons.")[1].split(".")[0]
        view = self.env.ref("%s.ebics_change_passphrase_view_form" % module)
        return {
            "name": _("EBICS keys change passphrase"),
            "view_type": "form",
            "view_mode": "form",
            "res_model": "ebics.change.passphrase",
            "view_id": view.id,
            "target": "new",
            "context": ctx,
            "type": "ir.actions.act_window",
        }

    def _update_passphrase_vals(self, vals):
        """
        Remove non-stored passphrases from db after e.g. successfull init_1
        """
        if vals["state"] in ("init", "get_bank_keys", "to_verify", "active_keys"):
            if not self.ebics_passphrase_store:
                vals["ebics_passphrase"] = False
            if self.ebics_sig_passphrase:
                vals["ebics_sig_passphrase"] = False
