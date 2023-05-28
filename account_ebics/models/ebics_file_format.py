# Copyright 2009-2023 Noviat.
# License LGPL-3 or later (http://www.gnu.org/licenses/lgpl).

from odoo import api, fields, models


class EbicsFileFormat(models.Model):
    _name = "ebics.file.format"
    _description = "EBICS File Formats"
    _order = "type,name,order_type"

    ebics_version = fields.Selection(
        selection=[
            ("2", "2"),
            ("3", "3"),
        ],
        string="EBICS protocol version",
        required=True,
        default="2",
    )
    name = fields.Char(
        string="Request Type",
        help="E.g. camt.xxx.cfonb120.stm, pain.001.001.03.sct.\n"
        "Specify camt.052, camt.053, camt.054 for camt "
        "Order Types such as C53, Z53, C54, Z54.\n"
        "This name has to match the 'Request Type' in your "
        "EBICS contract for Order Type 'FDL' or 'FUL'.\n",
    )
    type = fields.Selection(
        selection=[("down", "Download"), ("up", "Upload")], required=True
    )
    order_type = fields.Char(
        required=True,
        help="EBICS 3.0: BTD (download) or BTU (upload).\n"
        "EBICS 2.0: E.g. C53 (check your EBICS contract). "
        "For most banks in France you should use the "
        "format neutral Order Types 'FUL' for upload "
        "and 'FDL' for download.",
    )
    download_process_method = fields.Selection(
        selection="_selection_download_process_method",
        help="Enable processing within Odoo of the downloaded file "
        "via the 'Process' button."
        "E.g. specify camt.053 to import a camt.053 file and create "
        "a bank statement.",
    )
    # TODO:
    # move signature_class parameter so that it can be set per EBICS config
    signature_class = fields.Selection(
        selection=[("E", "Single signature"), ("T", "Transport signature")],
        help="Please doublecheck the security of your Odoo "
        "ERP system when using class 'E' to prevent unauthorised "
        "users to make supplier payments."
        "\nLeave this field empty to use the default "
        "defined for your EBICS UserID.",
    )
    description = fields.Char()
    suffix = fields.Char(
        help="Specify the filename suffix for this File Format.\nE.g. c53.xml",
    )
    # EBICS 3.0 BTF
    btf_service = fields.Char(
        string="BTF Service",
        help="BTF Service Name)\n"
        "The service code name consisting of 3 alphanumeric characters "
        "[A-Z0-9] (e.g. SCT, SDD, STM, EOP)",
    )
    btf_message = fields.Char(
        string="BTF Message Name",
        help="BTF Message Name\n"
        "The message name consisting of up to 10 alphanumeric characters "
        "[a-z0-9.] (eg. pain.001, pain.008, camt.053)",
    )
    btf_scope = fields.Char(
        string="BTF Scope",
        help="Scope of service.\n"
        "Either an ISO-3166 ALPHA 2 country code or an issuer code "
        "of 3 alphanumeric characters [A-Z0-9].",
    )
    btf_option = fields.Char(
        string="BTF Option",
        help="The service option code consisting of 3-10 alphanumeric "
        "characters [A-Z0-9] (eg. COR, B2B)",
    )
    btf_container = fields.Char(
        string="BTF Container",
        help="Type of container consisting of 3 characters [A-Z] (eg. XML, ZIP).",
    )
    btf_version = fields.Char(
        string="BTF Version",
        help="Message version consisting of 2 numeric characters [0-9] (eg. 03).",
    )
    btf_variant = fields.Char(
        string="BTF Variant",
        help="Message variant consisting of 3 numeric characters [0-9] (eg. 001).",
    )
    btf_format = fields.Char(
        string="BTF Format",
        help="Message format consisting of 1-4 alphanumeric characters [A-Z0-9] "
        "(eg. XML, JSON, PDF).",
    )

    @api.model
    def _selection_download_process_method(self):
        methods = self.env["ebics.file"]._file_format_methods().keys()
        return [(x, x) for x in methods]

    @api.onchange("type")
    def _onchange_type(self):
        if self.type == "up":
            self.download_process_method = False

    def name_get(self):
        res = []
        for rec in self:
            name = rec.ebics_version == "2" and rec.name or rec.btf_message
            if rec.description:
                name += " - " + rec.description
            res.append((rec.id, name))
        return res
