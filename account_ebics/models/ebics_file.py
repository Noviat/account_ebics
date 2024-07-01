# Copyright 2009-2024 Noviat.
# License LGPL-3 or later (http://www.gnu.org/licenses/lgpl).

import base64
import logging
from copy import deepcopy
from sys import exc_info
from traceback import format_exception

from lxml import etree

from odoo import _, fields, models
from odoo.exceptions import UserError

from odoo.addons.base.models.res_bank import sanitize_account_number

_logger = logging.getLogger(__name__)

DUP_CHECK_FORMATS = ["cfonb120", "camt053"]


class EbicsFile(models.Model):
    _name = "ebics.file"
    _description = "Object to store EBICS Data Files"
    _order = "date desc"
    _sql_constraints = [
        (
            "name_uniq",
            "unique (name, format_id)",
            "This File has already been down- or uploaded !",
        )
    ]

    name = fields.Char(string="Filename")
    data = fields.Binary(string="File", readonly=True)
    format_id = fields.Many2one(
        comodel_name="ebics.file.format", string="EBICS File Formats", readonly=True
    )
    type = fields.Selection(related="format_id.type", readonly=True)
    date_from = fields.Date(
        readonly=True, help="'Date From' as entered in the download wizard."
    )
    date_to = fields.Date(
        readonly=True, help="'Date To' as entered in the download wizard."
    )
    date = fields.Datetime(
        required=True, readonly=True, help="File Upload/Download date"
    )
    bank_statement_ids = fields.One2many(
        comodel_name="account.bank.statement",
        inverse_name="ebics_file_id",
        string="Generated Bank Statements",
        readonly=True,
    )
    state = fields.Selection(
        [("draft", "Draft"), ("done", "Done")],
        default="draft",
        required=True,
        readonly=True,
    )
    user_id = fields.Many2one(
        comodel_name="res.users",
        string="User",
        default=lambda self: self.env.user,
        readonly=True,
    )
    ebics_userid_id = fields.Many2one(
        comodel_name="ebics.userid",
        string="EBICS UserID",
        ondelete="restrict",
        readonly=True,
    )
    note = fields.Text(string="Notes")
    note_process = fields.Text(
        string="Process Notes",
        readonly=True,
    )
    company_ids = fields.Many2many(
        comodel_name="res.company",
        string="Companies",
        readonly=True,
        help="Companies sharing this EBICS file.",
    )

    def unlink(self):
        ff_methods = self._file_format_methods()
        for ebics_file in self:
            if ebics_file.state == "done":
                raise UserError(_("You can only remove EBICS files in state 'Draft'."))
            # execute format specific actions
            ff = ebics_file.format_id.download_process_method
            if ff in ff_methods:
                if ff_methods[ff].get("unlink"):
                    ff_methods[ff]["unlink"]()
            # remove bank statements
            ebics_file.bank_statement_ids.unlink()
        return super().unlink()

    def set_to_draft(self):
        return self.write({"state": "draft"})

    def set_to_done(self):
        return self.write({"state": "done"})

    def process(self):
        self.ensure_one()
        self = self.with_context(allowed_company_ids=self.env.user.company_ids.ids)
        self.note_process = ""
        ff_methods = self._file_format_methods()
        ff = self.format_id.download_process_method
        if ff in ff_methods:
            if ff_methods[ff].get("process"):
                res = ff_methods[ff]["process"]()
                self.state = "done"
                return res
        else:
            return self._process_undefined_format()

    def action_open_bank_statements(self):
        self.ensure_one()
        action = self.env["ir.actions.act_window"]._for_xml_id(
            "account.action_bank_statement_tree"
        )
        domain = [("id", "in", self.env.context.get("statement_ids"))]
        action["domain"] = domain
        return action

    def button_close(self):
        self.ensure_one()
        return {"type": "ir.actions.act_window_close"}

    def _file_format_methods(self):
        """
        Extend this dictionary in order to add support
        for extra file formats.
        """
        res = {
            "cfonb120": {
                "process": self._process_cfonb120,
                "unlink": self._unlink_cfonb120,
            },
            "camt.052": {
                "process": self._process_camt052,
                "unlink": self._unlink_camt052,
            },
            "camt.053": {
                "process": self._process_camt053,
                "unlink": self._unlink_camt053,
            },
            "camt.054": {
                "process": self._process_camt054,
                "unlink": self._unlink_camt054,
            },
            "pain.002": {
                "process": self._process_pain002,
                "unlink": self._unlink_pain002,
            },
        }
        return res

    def _check_import_module(self, module, raise_if_not_found=True):
        mod = (
            self.env["ir.module.module"]
            .sudo()
            .search([("name", "=like", module), ("state", "=", "installed")])
        )
        if not mod:
            if raise_if_not_found:
                raise UserError(
                    _(
                        "The module to process the '%(ebics_format)s' format is not installed "
                        "on your system. "
                        "\nPlease install module '%(module)s'",
                        ebics_format=self.format_id.name,
                        module=module,
                    )
                )
            return False
        return True

    def _lookup_journal(self, res, acc_number, currency_code):
        currency = self.env["res.currency"].search(
            [("name", "=ilike", currency_code)], limit=1
        )
        journal = self.env["account.journal"]
        if not currency:
            message = _("Currency %(cc)s not found.", cc=currency_code)
            res["notifications"].append({"type": "error", "message": message})
            return (currency, journal)

        journals = self.env["account.journal"].search(
            [
                ("type", "=", "bank"),
                (
                    "bank_account_id.sanitized_acc_number",
                    "ilike",
                    acc_number,
                ),
            ]
        )
        if not journals:
            message = _(
                "No financial journal found for Account Number %(nbr)s, "
                "Currency %(cc)s",
                nbr=acc_number,
                cc=currency_code,
            )
            res["notifications"].append({"type": "error", "message": message})
            return (currency, journal)

        for jrnl in journals:
            journal_currency = jrnl.currency_id or jrnl.company_id.currency_id
            if journal_currency != currency:
                continue
            else:
                journal = jrnl
                break

        if not journal:
            message = _(
                "No financial journal found for Account Number %(nbr)s, "
                "Currency %(cc)s",
                nbr=acc_number,
                cc=currency_code,
            )
            res["notifications"].append({"type": "error", "message": message})
        return (currency, journal)

    def _process_download_result(self, res, file_format=None):
        """
        We perform a duplicate statement check after the creation of the bank
        statements since we rely on Odoo Enterprise or OCA modules for the
        bank statement creation.
        From a development standpoint (code creation/maintenance) a check after
        creation is the easiest way.
        """
        statement_ids = res["statement_ids"]
        notifications = res["notifications"]
        statements = self.env["account.bank.statement"].sudo().browse(statement_ids)
        if statements:
            statements.write({"import_format": file_format})
            statements = self._statement_duplicate_check(res, statements)
        elif not notifications:
            notifications.append(
                {
                    "type": "warning",
                    "message": _("This file doesn't contain any transaction."),
                }
            )
        st_cnt = len(statements)
        warning_cnt = error_cnt = 0
        if notifications:
            errors = []
            warnings = []
            for notif in notifications:
                if isinstance(notif, dict) and notif["type"] == "error":
                    error_cnt += 1
                    parts = [notif[k] for k in notif if k in ("message", "details")]
                    errors.append("\n".join(parts))
                elif isinstance(notif, dict) and notif["type"] == "warning":
                    warning_cnt += 1
                    parts = [notif[k] for k in notif if k in ("message", "details")]
                    warnings.append("\n".join(parts))
                elif isinstance(notif, str):
                    warning_cnt += 1
                    warnings.append(notif + "\n")

        self.note_process += _("Process file %(fn)s results:", fn=self.name)
        if error_cnt:
            self.note_process += "\n\n" + _("Errors") + ":\n"
            self.note_process += "\n".join(errors)
            self.note_process += "\n\n"
            self.note_process += _("Number of errors: %(nr)s", nr=error_cnt)
        if warning_cnt:
            self.note_process += "\n\n" + _("Warnings") + ":\n"
            self.note_process += "\n".join(warnings)
            self.note_process += "\n\n"
            self.note_process += _("Number of warnings: %(nr)s", nr=warning_cnt)
            self.note_process += "\n"
        if st_cnt:
            self.note_process += "\n\n"
            self.note_process += _(
                "%(st_cnt)s bank statement%(sp)s been imported: ",
                st_cnt=st_cnt,
                sp=st_cnt == 1 and _(" has") or _("s have"),
            )
            self.note_process += "\n"
        for statement in statements:
            self.note_process += "\n" + _(
                "Statement %(st)s dated %(date)s (Company: %(cpy)s)",
                st=statement.name,
                date=statement.date,
                cpy=statement.company_id.name,
            )
        if statements:
            self.sudo().bank_statement_ids = [(4, x) for x in statements.ids]
        company_ids = self.sudo().bank_statement_ids.mapped("company_id").ids
        self.company_ids = [(6, 0, company_ids)]
        ctx = dict(self.env.context, statement_ids=statements.ids)
        module = __name__.split("addons.")[1].split(".")[0]
        result_view = self.env.ref("%s.ebics_file_view_form_result" % module)
        return {
            "name": _("Import EBICS File"),
            "res_id": self.id,
            "view_type": "form",
            "view_mode": "form",
            "res_model": self._name,
            "view_id": result_view.id,
            "target": "new",
            "context": ctx,
            "type": "ir.actions.act_window",
        }

    def _statement_duplicate_check(self, res, statements):
        """
        This check is required for import modules that do not
        set the 'unique_import_id' on the statement lines.
        E.g. OCA camt import
        """
        to_unlink = self.env["account.bank.statement"]
        for statement in statements.filtered(
            lambda r: r.import_format in DUP_CHECK_FORMATS
        ):
            dup = self.env["account.bank.statement"].search_count(
                [
                    ("id", "!=", statement.id),
                    ("name", "=", statement.name),
                    ("company_id", "=", statement.company_id.id),
                    ("date", "=", statement.date),
                    ("import_format", "=", statement.import_format),
                ]
            )
            if dup:
                message = _(
                    "Statement %(st_name)s dated %(date)s has already been imported.",
                    st_name=statement.name,
                    date=statement.date,
                )
                res["notifications"].append({"type": "warning", "message": message})
                to_unlink += statement
        res["statement_ids"] = [
            x for x in res["statement_ids"] if x not in to_unlink.ids
        ]
        statements -= to_unlink
        to_unlink.unlink()
        return statements

    def _process_cfonb120(self):
        import_module = "account_statement_import_fr_cfonb"
        self._check_import_module(import_module)
        res = {"statement_ids": [], "notifications": []}
        st_datas = self._split_cfonb(res)
        if st_datas:
            self._process_bank_statement_oca(res, st_datas)
        return self._process_download_result(res, file_format="cfonb120")

    def _unlink_cfonb120(self):
        """
        Placeholder for cfonb120 specific actions before removing the
        EBICS data file and its related bank statements.
        """

    def _split_cfonb(self, res):
        """
        Split CFONB file received via EBICS per statement.
        Statements without transactions are removed.
        """
        datas = []
        file_data = base64.b64decode(self.data)
        file_data.replace(b"\n", b"").replace(b"\r", b"")
        if len(file_data) % 120:
            message = _(
                "Incorrect CFONB120 file:\n"
                "the file is not divisible in 120 char lines"
            )
            res["notifications"].append({"type": "error", "message": message})
            return datas

        lines = []
        for i in range(0, len(file_data), 120):
            lines.append(file_data[i : i + 120])

        st_lines = b""
        transactions = False
        for line in lines:
            rec_type = line[0:2]
            currency_code = line[16:19].decode()
            acc_number = line[21:32].decode()
            st_lines += line + b"\n"
            if rec_type == b"04":
                transactions = True
            if rec_type == b"07":
                if transactions:
                    currency, journal = self._lookup_journal(
                        res, acc_number, currency_code
                    )
                    if currency and journal:
                        datas.append(
                            {
                                "acc_number": acc_number,
                                "journal_id": journal.id,
                                "company_id": journal.company_id.id,
                                "data": base64.b64encode(st_lines),
                            }
                        )
                st_lines = b""
                transactions = False
        return datas

    def _process_camt052(self):
        import_module = "account_statement_import_camt"
        self._check_import_module(import_module)
        return self._process_camt053(file_format="camt052")

    def _unlink_camt052(self):
        """
        Placeholder for camt052 specific actions before removing the
        EBICS data file and its related bank statements.
        """

    def _process_camt054(self):
        import_module = "account_statement_import_camt"
        self._check_import_module(import_module)
        return self._process_camt053(file_format="camt054")

    def _unlink_camt054(self):
        """
        Placeholder for camt054 specific actions before removing the
        EBICS data file and its related bank statements.
        """

    def _process_camt053(self, file_format=None):
        """
        The Odoo standard statement import is based on manual selection
        of a financial journal before importing the electronic statement file.
        An EBICS download may return a single file containing a large number of
        statements from different companies/journals.
        Hence we need to split the CAMT file into
        single statement CAMT files before we can call the logic
        implemented by the Odoo OE or Community CAMT parsers.
        """
        modules = [
            ("oca", "account_statement_import_camt"),
            ("oe", "account_bank_statement_import_camt"),
        ]
        author = False
        for entry in modules:
            if self._check_import_module(entry[1], raise_if_not_found=False):
                author = entry[0]
                break
        if not author:
            raise UserError(
                _(
                    "The module to process the '%(ebics_format)s' format is "
                    "not installed on your system. "
                    "\nPlease install one of the following modules: \n%(modules)s.",
                    ebics_format=self.format_id.name,
                    modules=", ".join([x[1] for x in modules]),
                )
            )
        res = {"statement_ids": [], "notifications": []}
        st_datas = self._split_camt(res)
        if author == "oca":
            self._process_bank_statement_oca(res, st_datas)
        else:
            self._process_bank_statement_oe(res, st_datas)
        file_format = file_format or "camt053"
        return self._process_download_result(res, file_format=file_format)

    def _process_bank_statement_oca(self, res, st_datas):
        for st_data in st_datas:
            try:
                with self.env.cr.savepoint():
                    self._create_bank_statement_oca(res, st_data)
            except UserError as e:
                res["notifications"].append(
                    {"type": "error", "message": "".join(e.args)}
                )
            except Exception:
                tb = "".join(format_exception(*exc_info()))
                res["notifications"].append({"type": "error", "message": tb})

    def _create_bank_statement_oca(self, res, st_data):
        wiz = (
            self.env["account.statement.import"]
            .with_company(st_data["company_id"])
            .with_context(active_model="ebics.file")
            .create({"statement_filename": self.name})
        )
        wiz.import_single_file(base64.b64decode(st_data["data"]), res)

    def _process_bank_statement_oe(self, res, st_datas):
        """
        We execute a cr.commit() after every statement import since we get a
        'savepoint does not exist' error when using 'with self.env.cr.savepoint()'.
        """
        for st_data in st_datas:
            try:
                self._create_bank_statement_oe(res, st_data)
                self.env.cr.commit()  # pylint: disable=E8102
            except UserError as e:
                msg = "".join(e.args)
                msg += "\n"
                msg += _(
                    "Statement for Account Number %(nr)s has not been processed.",
                    nr=st_data["acc_number"],
                )
                res["notifications"].append({"type": "error", "message": msg})
            except Exception:
                tb = "".join(format_exception(*exc_info()))
                res["notifications"].append({"type": "error", "message": tb})

    def _create_bank_statement_oe(self, res, st_data):
        attachment = (
            self.env["ir.attachment"]
            .with_company(st_data["company_id"])
            .create(
                {
                    "name": self.name,
                    "datas": st_data["data"],
                    "store_fname": self.name,
                }
            )
        )
        journal = (
            self.env["account.journal"]
            .with_company(st_data["company_id"])
            .browse(st_data["journal_id"])
        )
        act = journal._import_bank_statement(attachment)
        for entry in act["domain"]:
            if (
                isinstance(entry, tuple)
                and entry[0] == "statement_id"
                and entry[1] == "in"
            ):
                res["statement_ids"].extend(entry[2])
                break
        notifications = act["context"]["notifications"]
        if notifications:
            res["notifications"].append(act["context"]["notifications"])

    def _unlink_camt053(self):
        """
        Placeholder for camt053 specific actions before removing the
        EBICS data file and its related bank statements.
        """

    def _split_camt(self, res):
        """
        Split CAMT file received via EBICS per statement.
        Statements without transactions are removed.
        """
        datas = []
        file_data = base64.b64decode(self.data)
        root = etree.fromstring(file_data, parser=etree.XMLParser(recover=True))
        if root is None:
            message = _("Invalid XML file.")
            res["notifications"].append({"type": "error", "message": message})
        ns = {k or "ns": v for k, v in root.nsmap.items()}
        camt_variant = ns["ns"].split("camt.")[1][:3]
        variant_tags = {
            "052": "Rpt",
            "053": "Stmt",
            "054": "Ntfctn",
        }
        camt_tag = variant_tags[camt_variant]
        stmts = root[0].findall("ns:{}".format(camt_tag), ns)
        for i, stmt in enumerate(stmts):
            acc_number = sanitize_account_number(
                stmt.xpath(
                    "ns:Acct/ns:Id/ns:IBAN/text() | ns:Acct/ns:Id/ns:Othr/ns:Id/text()",
                    namespaces=ns,
                )[0]
            )
            if not acc_number:
                message = _("No bank account number found.")
                res["notifications"].append({"type": "error", "message": message})
                continue
            currency_code = stmt.xpath(
                "ns:Acct/ns:Ccy/text() | ns:Bal/ns:Amt/@Ccy", namespaces=ns
            )[0]
            # some banks (e.g. COMMERZBANK) add the currency as the last 3 digits
            # of the bank account number hence we need to remove this since otherwise
            # the journal matching logic fails
            if acc_number[-3:] == currency_code:
                acc_number = acc_number[:-3]

            root_new = deepcopy(root)
            entries = False
            for j, el in enumerate(root_new[0].findall("ns:{}".format(camt_tag), ns)):
                if j != i:
                    el.getparent().remove(el)
                else:
                    entries = el.findall("ns:Ntry", ns)
            if not entries:
                continue
            else:
                currency, journal = self._lookup_journal(res, acc_number, currency_code)
                if not (currency and journal):
                    continue
                datas.append(
                    {
                        "acc_number": acc_number,
                        "journal_id": journal.id,
                        "company_id": journal.company_id.id,
                        "data": base64.b64encode(etree.tostring(root_new)),
                    }
                )

        return datas

    def _process_pain002(self):
        """
        Placeholder for processing pain.002 files.
        TODO:
        add import logic based upon OCA 'account_payment_return_import'
        """

    def _unlink_pain002(self):
        """
        Placeholder for pain.002 specific actions before removing the
        EBICS data file.
        """
        raise NotImplementedError

    def _process_undefined_format(self):
        raise UserError(
            _(
                "The current version of the 'account_ebics' module "
                "has no support to automatically process EBICS files "
                "with format %s."
            )
            % self.format_id.name
        )
