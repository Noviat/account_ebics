# Copyright 2009-2023 Noviat.
# License AGPL-3 or later (http://www.gnu.org/licenses/agpl).

import logging
import os
import re

from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class EbicsConfig(models.Model):
    """
    EBICS configuration is stored in a separate object in order to
    allow extra security policies on this object.
    """

    _name = "ebics.config"
    _description = "EBICS Configuration"
    _order = "name"

    name = fields.Char(
        readonly=True,
        states={"draft": [("readonly", False)]},
        required=True,
    )
    journal_ids = fields.Many2many(
        comodel_name="account.journal",
        relation="account_journal_ebics_config_rel",
        readonly=True,
        states={"draft": [("readonly", False)]},
        string="Bank Accounts",
        domain="[('type', '=', 'bank')]",
    )
    ebics_host = fields.Char(
        string="EBICS HostID",
        required=True,
        readonly=True,
        states={"draft": [("readonly", False)]},
        help="Contact your bank to get the EBICS HostID."
        "\nIn France the BIC is usually allocated to the HostID "
        "whereas in Germany it tends to be an institute specific string "
        "of 8 characters.",
    )
    ebics_url = fields.Char(
        string="EBICS URL",
        required=True,
        readonly=True,
        states={"draft": [("readonly", False)]},
        help="Contact your bank to get the EBICS URL.",
    )
    ebics_version = fields.Selection(
        selection=[
            ("H003", "H003 (2.4)"),
            ("H004", "H004 (2.5)"),
            ("H005", "H005 (3.0)"),
        ],
        string="EBICS protocol version",
        readonly=True,
        states={"draft": [("readonly", False)]},
        required=True,
        default="H004",
    )
    ebics_partner = fields.Char(
        string="EBICS PartnerID",
        required=True,
        readonly=True,
        states={"draft": [("readonly", False)]},
        help="Organizational unit (company or individual) "
        "that concludes a contract with the bank. "
        "\nIn this contract it will be agreed which order types "
        "(file formats) are used, which accounts are concerned, "
        "which of the customer's users (subscribers) "
        "communicate with the EBICS bank server and the authorisations "
        "that these users will possess. "
        "\nIt is identified by the PartnerID.",
    )
    ebics_userid_ids = fields.One2many(
        comodel_name="ebics.userid",
        inverse_name="ebics_config_id",
        string="EBICS UserID",
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
    ebics_files = fields.Char(
        string="EBICS Files Root",
        required=True,
        readonly=True,
        states={"draft": [("readonly", False)]},
        default=lambda self: self._default_ebics_files(),
        help="Root Directory for EBICS File Transfer Folders.",
    )
    # We store the EBICS keys in a separate directory in the file system.
    # This directory requires special protection to reduce fraude.
    ebics_keys = fields.Char(
        string="EBICS Keys Root",
        required=True,
        readonly=True,
        states={"draft": [("readonly", False)]},
        default=lambda self: self._default_ebics_keys(),
        help="Root Directory for storing the EBICS Keys.",
    )
    ebics_key_version = fields.Selection(
        selection=[("A005", "A005 (RSASSA-PKCS1-v1_5)"), ("A006", "A006 (RSASSA-PSS)")],
        string="EBICS key version",
        default="A006",
        readonly=True,
        states={"draft": [("readonly", False)]},
        help="The key version of the electronic signature.",
    )
    ebics_key_bitlength = fields.Integer(
        string="EBICS key bitlength",
        default=2048,
        readonly=True,
        states={"draft": [("readonly", False)]},
        help="The bit length of the generated keys. "
        "\nThe value must be between 1536 and 4096.",
    )
    ebics_file_format_ids = fields.Many2many(
        comodel_name="ebics.file.format",
        column1="config_id",
        column2="format_id",
        string="EBICS File Format",
        readonly=True,
        states={"draft": [("readonly", False)]},
    )
    state = fields.Selection(
        [("draft", "Draft"), ("confirm", "Confirmed")],
        default="draft",
        required=True,
        readonly=True,
    )
    order_number = fields.Char(
        size=4,
        readonly=True,
        states={"draft": [("readonly", False)]},
        help="Specify the number for the next order."
        "\nThis number should match the following pattern : "
        "[A-Z]{1}[A-Z0-9]{3}",
    )
    active = fields.Boolean(default=True)
    company_ids = fields.Many2many(
        comodel_name="res.company",
        relation="ebics_config_res_company_rel",
        string="Companies",
        readonly=True,
        help="Companies sharing this EBICS contract.",
    )

    @api.model
    def _default_ebics_files(self):
        return "/".join(["/home/odoo/ebics_files", self._cr.dbname])

    @api.model
    def _default_ebics_keys(self):
        return "/".join(["/etc/odoo/ebics_keys", self._cr.dbname])

    @api.constrains("ebics_key_bitlength")
    def _check_ebics_key_bitlength(self):
        for cfg in self:
            if cfg.ebics_version == "H005" and cfg.ebics_key_bitlength < 2048:
                raise UserError(_("EBICS key bitlength must be >= 2048."))

    @api.constrains("order_number")
    def _check_order_number(self):
        for cfg in self:
            nbr = cfg.order_number
            ok = True
            if nbr:
                if len(nbr) != 4:
                    ok = False
                else:
                    pattern = re.compile("[A-Z]{1}[A-Z0-9]{3}")
                    if not pattern.match(nbr):
                        ok = False
            if not ok:
                raise UserError(
                    _(
                        "Order Number should comply with the following pattern:"
                        "\n[A-Z]{1}[A-Z0-9]{3}"
                    )
                )

    def write(self, vals):
        """
        Due to the multi-company nature of the EBICS config we
        need to adapt the company_ids in the write method.
        """
        if "journal_ids" not in vals:
            return super().write(vals)
        for rec in self:
            old_company_ids = rec.journal_ids.mapped("company_id").ids
            super(EbicsConfig, rec).write(vals)
            new_company_ids = rec.journal_ids.mapped("company_id").ids
            updates = []
            for cid in new_company_ids:
                if cid in old_company_ids:
                    old_company_ids.remove(cid)
                else:
                    updates += [(4, cid)]
            updates += [(3, x) for x in old_company_ids]
            super(EbicsConfig, rec).write({"company_ids": updates})
        return True

    def unlink(self):
        for ebics_config in self:
            if ebics_config.state == "active":
                raise UserError(_("You cannot remove active EBICS configurations."))
        return super().unlink()

    def set_to_draft(self):
        return self.write({"state": "draft"})

    def set_to_confirm(self):
        return self.write({"state": "confirm"})

    def _get_order_number(self):
        return self.order_number

    def _update_order_number(self, OrderID):
        o_list = list(OrderID)
        for i, c in enumerate(reversed(o_list), start=1):
            if c == "9":
                o_list[-i] = "A"
                break
            if c == "Z":
                o_list[-i] = "0"
                continue
            else:
                o_list[-i] = chr(ord(c) + 1)
                break
        next_order_number = "".join(o_list)
        if next_order_number == "ZZZZ":
            next_order_number = "A000"
        self.order_number = next_order_number

    def _check_ebics_keys(self):
        dirname = self.ebics_keys or ""
        if not os.path.exists(dirname):
            raise UserError(
                _(
                    "EBICS Keys Root Directory %s is not available."
                    "\nPlease contact your system administrator."
                )
                % dirname
            )

    def _check_ebics_files(self):
        dirname = self.ebics_files or ""
        if not os.path.exists(dirname):
            raise UserError(
                _(
                    "EBICS Files Root Directory %s is not available."
                    "\nPlease contact your system administrator."
                )
                % dirname
            )
