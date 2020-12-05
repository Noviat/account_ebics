# Copyright 2009-2020 Noviat.
# License LGPL-3 or later (http://www.gnu.org/licenses/lpgl).

from odoo import api, fields, models


class EbicsFileFormat(models.Model):
    _name = 'ebics.file.format'
    _description = 'EBICS File Formats'
    _order = 'type,name,order_type'

    name = fields.Char(
        string='Request Type',
        required=True,
        help="E.g. camt.xxx.cfonb120.stm, pain.001.001.03.sct.\n"
             "Specify camt.052, camt.053, camt.054 for camt "
             "Order Types such as C53, Z53, C54, Z54.\n"
             "This name has to match the 'Request Type' in your "
             "EBICS contract for Order Type 'FDL' or 'FUL'.\n")
    type = fields.Selection(
        selection=[('down', 'Download'),
                   ('up', 'Upload')],
        required=True)
    order_type = fields.Char(
        string='Order Type',
        required=True,
        help="E.g. C53 (check your EBICS contract).\n"
             "For most banks in France you should use the "
             "format neutral Order Types 'FUL' for upload "
             "and 'FDL' for download.")
    download_process_method = fields.Selection(
        selection='_selection_download_process_method',
        help="Enable processing within Odoo of the downloaded file "
             "via the 'Process' button."
             "E.g. specify camt.053 to import a camt.053 file and create "
             "a bank statement.")
    # TODO:
    # move signature_class parameter so that it can be set per EBICS config
    signature_class = fields.Selection(
        selection=[('E', 'Single signature'),
                   ('T', 'Transport signature')],
        string='Signature Class',
        help="Please doublecheck the security of your Odoo "
             "ERP system when using class 'E' to prevent unauthorised "
             "users to make supplier payments."
             "\nLeave this field empty to use the default "
             "defined for your EBICS Configuration.")
    description = fields.Char()
    suffix = fields.Char(
        required=True,
        help="Specify the filename suffix for this File Format."
             "\nE.g. c53.xml")

    @api.model
    def _selection_download_process_method(self):
        methods = self.env['ebics.file']._file_format_methods().keys()
        return [(x, x) for x in methods]

    @api.onchange('type')
    def _onchange_type(self):
        if self.type == 'up':
            self.download_process_method = False
