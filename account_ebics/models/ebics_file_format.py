# Copyright 2009-2020 Noviat.
# License LGPL-3 or later (http://www.gnu.org/licenses/lpgl).

from odoo import api, fields, models


class EbicsFileFormat(models.Model):
    _name = 'ebics.file.format'
    _description = 'EBICS File Formats'
    _order = 'type,name'

    name = fields.Selection(
        selection=lambda self: self._selection_name(),
        string='Request Type', required=True)
    type = fields.Selection(
        selection=[('down', 'Download'),
                   ('up', 'Upload')],
        required=True)
    order_type = fields.Selection(
        selection=lambda self: self._selection_order_type(),
        string='Order Type',
        help="For most banks is France you should use the "
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

    @api.model
    def _selection_order_type(self):
        up = self._supported_upload_order_types()
        down = self._supported_download_order_types()
        selection = [(x, x) for x in up + down]
        return selection

    def _supported_upload_order_types(self):
        return ['FUL', 'CCT', 'CDD', 'CDB', 'XE2', 'XE3']

    def _supported_download_order_types(self):
        return ['FDL', 'C52', 'C53', 'C54']

    @api.model
    def _selection_name(self):
        """
        List of supported EBICS Request Types.
        Extend this method via a custom module when testing
        a new Request Type and make a PR for the
        account_ebics module when this new Request Type
        is working correctly.
        This PR should include at least updates to
        - 'data/ebics_file_format.xml'
        - 'models/ebics_file_format.py'
        An overview of the EBICS Request Types can be found in
        the doc folder of this module (EBICS_Annex2).
        """
        request_types = [
            'camt.052.001.02.stm',
            'camt.053.001.02.stm',
            'pain.001.001.03.sct',
            'pain.008.001.02.sdd',
            'pain.008.001.02.sbb',
            'camt.xxx.cfonb120.stm',
            'pain.001.001.02.sct',
            'camt.053',
            'pain.001',
            'pain.008',
        ]
        selection = [(x, x) for x in request_types]
        return selection
