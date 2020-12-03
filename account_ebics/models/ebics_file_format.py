# Copyright 2009-2020 Noviat.
# License LGPL-3 or later (http://www.gnu.org/licenses/lpgl).

from odoo import fields, models


class EbicsFileFormat(models.Model):
    _name = 'ebics.file.format'
    _description = 'EBICS File Formats'
    _order = 'type,name'

    name = fields.Char(
        string='Request Type',
        required=True,
        help="E.g. camt.053.001.02.stm, camt.xxx.cfonb120.stm, "
             "pain.001.001.03.sct (check your EBICS contract).\n")
    type = fields.Selection(
        selection=[('down', 'Download'),
                   ('up', 'Upload')],
        required=True)
    order_type = fields.Char(
        string='Order Type',
        help="E.g. C53 (check your EBICS contract).\n"
             "For most banks in France you should use the "
             "format neutral Order Types 'FUL' for upload "
             "and 'FDL' for download.")
    signature_class = fields.Selection(
        selection=[('E', 'Single signature'),
                   ('T', 'Transport signature')],
        string='Signature Class',
        help="Please doublecheck the security of your Odoo "
             "ERP system when using class 'E' to prevent unauthorised "
             "users to make supplier payments."
             "\nLeave this field empty to use the default "
             "defined for your bank connection.")
    description = fields.Char()
    suffix = fields.Char(
        required=True,
        help="Specify the filename suffix for this File Format."
             "\nE.g. camt.053.xml")
