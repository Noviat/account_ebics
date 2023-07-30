# Copyright 2009-2023 Noviat.
# License LGPL-3 or later (http://www.gnu.org/licenses/lgpl).

import base64
import logging
from copy import deepcopy
from sys import exc_info
from traceback import format_exception

from lxml import etree

from odoo import _, fields, models
from odoo.exceptions import UserError
from odoo.tools.safe_eval import safe_eval

from odoo.addons.base.models.res_bank import sanitize_account_number

_logger = logging.getLogger(__name__)


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

    def _process_download_result(self, res):
        statement_ids = res["statement_ids"]
        notifications = res["notifications"]
        statements = self.env["account.bank.statement"].sudo().browse(statement_ids)
        st_cnt = len(statement_ids)
        warning_cnt = error_cnt = 0
        if notifications:
            for notif in notifications:
                if notif["type"] == "error":
                    error_cnt += 1
                elif notif["type"] == "warning":
                    warning_cnt += 1
                parts = [notif[k] for k in notif if k in ("message", "details")]
                self.note_process += "\n".join(parts)
                self.note_process += "\n\n"
            self.note_process += "\n"
        if error_cnt:
            self.note_process += (
                _("Number of errors detected during import: %s") % error_cnt
            )
            self.note_process += "\n"
        if warning_cnt:
            self.note_process += (
                _("Number of warnings detected during import: %s") % warning_cnt
            )
        if st_cnt:
            self.note_process += "\n\n"
            self.note_process += _(
                "%(st_cnt)s bank statement%(sp)s been imported: ",
                st_cnt=st_cnt,
                sp=st_cnt == 1 and _(" has") or _("s have"),
            )
            self.note_process += "\n"
        for statement in statements:
            self.note_process += ("\n%s, %s (%s)") % (
                statement.date,
                statement.name,
                statement.company_id.name,
            )
        if statement_ids:
            self.sudo().bank_statement_ids = [(4, x) for x in statement_ids]
        company_ids = self.sudo().bank_statement_ids.mapped("company_id").ids
        self.company_ids = [(6, 0, company_ids)]
        ctx = dict(self.env.context, statement_ids=statement_ids)
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

    def _process_cfonb120(self):
        """
        Disable this code while waiting on OCA cfonb release for 16.0
        """
        # pylint: disable=W0101
        raise NotImplementedError

        import_module = "account_statement_import_fr_cfonb"
        self._check_import_module(import_module)
        wiz_model = "account.statement.import"
        data_file = base64.b64decode(self.data)
        lines = data_file.split(b"\n")
        wiz_vals_list = []
        st_lines = b""
        transactions = False
        for line in lines:
            rec_type = line[0:2]
            acc_number = line[21:32]
            st_lines += line + b"\n"
            if rec_type == b"04":
                transactions = True
            if rec_type == b"07":
                if transactions:
                    fn = "_".join([acc_number.decode(), self.name])
                    wiz_vals_list.append(
                        {
                            "statement_filename": fn,
                            "statement_file": base64.b64encode(st_lines),
                        }
                    )
                st_lines = b""
                transactions = False
        result_action = self.env["ir.actions.act_window"]._for_xml_id(
            "account.action_bank_statement_tree"
        )
        result_action["context"] = safe_eval(result_action["context"])
        statement_ids = []
        notifications = []
        for i, wiz_vals in enumerate(wiz_vals_list, start=1):
            result = {
                "statement_ids": [],
                "notifications": [],
            }
            statement_filename = wiz_vals["statement_filename"]
            wiz = (
                self.env[wiz_model]
                .with_context(active_model="ebics.file")
                .create(wiz_vals)
            )
            try:
                with self.env.cr.savepoint():
                    file_data = base64.b64decode(wiz_vals["statement_file"])
                    msg_hdr = _(
                        "{} : Import failed for statement number %(index)s, filename %(fn)s:\n",
                        index=i,
                        fn=statement_filename,
                    )
                    wiz.import_single_file(file_data, result)
                    if not result["statement_ids"]:
                        message = msg_hdr.format(_("Warning"))
                        message += _(
                            "You have already imported this file, or this file "
                            "only contains already imported transactions."
                        )
                        notifications += [
                            {
                                "type": "warning",
                                "message": message,
                            }
                        ]
                    else:
                        statement_ids.extend(result["statement_ids"])
                    notifications.extend(result["notifications"])

            except UserError as e:
                message = msg_hdr.format(_("Error"))
                message += "".join(e.args)
                notifications += [
                    {
                        "type": "error",
                        "message": message,
                    }
                ]

            except Exception:
                tb = "".join(format_exception(*exc_info()))
                message = msg_hdr.format(_("Error"))
                message += tb
                notifications += [
                    {
                        "type": "error",
                        "message": message,
                    }
                ]

        result_action["context"]["notifications"] = notifications
        result_action["domain"] = [("id", "in", statement_ids)]
        return self._process_result_action(result_action)

    def _unlink_cfonb120(self):
        """
        Placeholder for cfonb120 specific actions before removing the
        EBICS data file and its related bank statements.
        """

    def _process_camt052(self):
        import_module = "account_statement_import_camt"
        self._check_import_module(import_module)
        return self._process_camt053(self)

    def _unlink_camt052(self):
        """
        Placeholder for camt052 specific actions before removing the
        EBICS data file and its related bank statements.
        """

    def _process_camt054(self):
        import_module = "account_statement_import_camt"
        self._check_import_module(import_module)
        return self._process_camt053(self)

    def _unlink_camt054(self):
        """
        Placeholder for camt054 specific actions before removing the
        EBICS data file and its related bank statements.
        """

    def _process_camt053(self):
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
        msg_hdr = _("{} : Import failed for file %(fn)s:\n", fn=self.name)
        try:
            if author == "oca":
                self._process_camt053_oca(res, st_datas)
            else:
                self._process_camt053_oe(res, st_datas)
        except UserError as e:
            message = msg_hdr.format(_("Error"))
            message += "".join(e.args)
            res["notifications"].append({"type": "error", "message": message})
        except Exception:
            tb = "".join(format_exception(*exc_info()))
            message = msg_hdr.format(_("Error"))
            message += tb
            res["notifications"].append({"type": "error", "message": message})

        return self._process_download_result(res)

    def _process_camt053_oca(self, res, st_datas):
        raise NotImplementedError

    def _process_camt053_oe(self, res, st_datas):
        """
        We execute a cr.commit() after every statement import since we get a
        'savepoint does not exist' error when using 'with self.env.cr.savepoint()'.
        """
        for st_data in st_datas:
            self._create_statement_camt053_oe(res, st_data)
            self.env.cr.commit()  # pylint: disable=E8102

    def _create_statement_camt053_oe(self, res, st_data):
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
        msg_hdr = _("{} : Import failed for file %(fn)s:\n", fn=self.name)
        file_data = base64.b64decode(self.data)
        root = etree.fromstring(file_data, parser=etree.XMLParser(recover=True))
        if root is None:
            message = msg_hdr.format(_("Error"))
            message += _("Invalid XML file.")
            res["notifications"].append({"type": "error", "message": message})
        ns = {k or "ns": v for k, v in root.nsmap.items()}
        for i, stmt in enumerate(root[0].findall("ns:Stmt", ns), start=1):
            msg_hdr = _(
                "{} : Import failed for statement number %(index)s, filename %(fn)s:\n",
                index=i,
                fn=self.name,
            )
            acc_number = sanitize_account_number(
                stmt.xpath(
                    "ns:Acct/ns:Id/ns:IBAN/text() | ns:Acct/ns:Id/ns:Othr/ns:Id/text()",
                    namespaces=ns,
                )[0]
            )
            if not acc_number:
                message = msg_hdr.format(_("Error"))
                message += _("No bank account number found.")
                res["notifications"].append({"type": "error", "message": message})
                continue
            currency_code = stmt.xpath(
                "ns:Acct/ns:Ccy/text() | ns:Bal/ns:Amt/@Ccy", namespaces=ns
            )[0]
            currency = self.env["res.currency"].search(
                [("name", "=ilike", currency_code)], limit=1
            )
            if not currency:
                message = msg_hdr.format(_("Error"))
                message += _("Currency %(cc)s not found.", cc=currency_code)
                res["notifications"].append({"type": "error", "message": message})
                continue
            journal = self.env["account.journal"].search(
                [
                    ("type", "=", "bank"),
                    (
                        "bank_account_id.sanitized_acc_number",
                        "ilike",
                        acc_number,
                    ),
                ]
            )
            if not journal:
                message = msg_hdr.format(_("Error"))
                message += _(
                    "No financial journal found for Account Number %(nbr)s, "
                    "Currency %(cc)s",
                    nbr=acc_number,
                    cc=currency_code,
                )
                res["notifications"].append({"type": "error", "message": message})
                continue

            journal_currency = journal.currency_id or journal.company_id.currency_id
            if journal_currency != currency:
                message = msg_hdr.format(_("Error"))
                message += _(
                    "No financial journal found for Account Number %(nbr)s, "
                    "Currency %(cc)s",
                    nbr=acc_number,
                    cc=currency_code,
                )
                res["notifications"].append({"type": "error", "message": message})
                continue

            root_new = deepcopy(root)
            entries = False
            for j, el in enumerate(root_new[0].findall("ns:Stmt", ns), start=1):
                if j != i:
                    el.getparent().remove(el)
                else:
                    entries = el.findall("ns:Ntry", ns)
            if not entries:
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
