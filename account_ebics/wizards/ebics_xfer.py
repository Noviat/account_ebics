# Copyright 2009-2020 Noviat.
# License LGPL-3 or later (http://www.gnu.org/licenses/lpgl).

"""
import logging
logging.basicConfig(
    level=logging.DEBUG,
    format='[%(asctime)s] %(levelname)s - %(name)s: %(message)s')
"""

import base64
import logging
import os
from sys import exc_info
from traceback import format_exception

from odoo import api, fields, models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

try:
    import fintech
    from fintech.ebics import EbicsKeyRing, EbicsBank, EbicsUser, EbicsClient,\
        EbicsFunctionalError, EbicsTechnicalError, EbicsVerificationError
    fintech.cryptolib = 'cryptography'
except ImportError:
    EbicsBank = object
    _logger.warning('Failed to import fintech')


class EbicsBank(EbicsBank):

    def _next_order_id(self, partnerid):
        """
        EBICS protocol version H003 requires generation of the OrderID.
        The OrderID must be a string between 'A000' and 'ZZZZ' and
        unique for each partner id.
        """
        return hasattr(self, '_order_number') and self._order_number or 'A000'


class EbicsXfer(models.TransientModel):
    _name = 'ebics.xfer'
    _description = 'EBICS file transfer'

    ebics_config_id = fields.Many2one(
        comodel_name='ebics.config',
        string='EBICS Configuration',
        domain=[('state', '=', 'confirm')],
        default=lambda self: self._default_ebics_config_id())
    ebics_userid_id = fields.Many2one(
        comodel_name='ebics.userid',
        string='EBICS UserID')
    ebics_passphrase = fields.Char(
        string='EBICS Passphrase')
    date_from = fields.Date()
    date_to = fields.Date()
    upload_data = fields.Binary(string='File to Upload')
    upload_fname = fields.Char(
        string='Upload Filename', default='')
    upload_fname_dummy = fields.Char(
        related='upload_fname', string='Upload Filename', readonly=True)
    format_id = fields.Many2one(
        comodel_name='ebics.file.format',
        string='EBICS File Format',
        help="Select EBICS File Format to upload/download."
             "\nLeave blank to download all available files.")
    order_type = fields.Selection(
        selection=lambda self: self._selection_order_type(),
        string='Order Type',
        help="For most banks is France you should use the "
             "format neutral Order Types 'FUL' for upload "
             "and 'FDL' for download.")
    test_mode = fields.Boolean(
        string='Test Mode',
        help="Select this option to test if the syntax of "
             "the upload file is correct."
             "\nThis option is only available for "
             "Order Type 'FUL'.")
    note = fields.Text(string='EBICS file transfer Log', readonly=True)

    @api.model
    def _default_ebics_config_id(self):
        cfg_mod = self.env['ebics.config']
        cfg = cfg_mod.search(
            [('company_ids', 'in', self.env.user.company_ids.ids),
             ('state', '=', 'confirm')])
        if cfg and len(cfg) == 1:
            return cfg
        else:
            return cfg_mod

    @api.model
    def _selection_order_type(self):
        return self.env['ebics.file.format']._selection_order_type()

    @api.onchange('ebics_config_id')
    def _onchange_ebics_config_id(self):
        ebics_userids = self.ebics_config_id.ebics_userid_ids
        domain = {'ebics_userid_id': [('id', 'in', ebics_userids.ids)]}
        if self._context.get('ebics_download'):
            download_formats = self.ebics_config_id.ebics_file_format_ids\
                .filtered(lambda r: r.type == 'down')
            if len(download_formats) == 1:
                self.format_id = download_formats
            domain['format_id'] = [('type', '=', 'down'),
                                   ('id', 'in', download_formats.ids)]
            if len(ebics_userids) == 1:
                self.ebics_userid_id = ebics_userids
            else:
                transport_users = ebics_userids.filtered(
                    lambda r: r.signature_class == 'T')
                if len(transport_users) == 1:
                    self.ebics_userid_id = transport_users
        else:
            upload_formats = self.ebics_config_id.ebics_file_format_ids\
                .filtered(lambda r: r.type == 'up')
            if len(upload_formats) == 1:
                self.format_id = upload_formats
            domain['format_id'] = [('type', '=', 'up'),
                                   ('id', 'in', upload_formats.ids)]
            if len(ebics_userids) == 1:
                self.ebics_userid_id = ebics_userids
        return {'domain': domain}

    @api.onchange('upload_data')
    def _onchange_upload_data(self):
        self.upload_fname_dummy = self.upload_fname
        self._detect_upload_format()
        upload_formats = self.format_id \
            or self.ebics_config_id.ebics_file_format_ids.filtered(
                lambda r: r.type == 'up')
        if len(upload_formats) == 1:
            self.format_id = upload_formats

    @api.onchange('format_id')
    def _onchange_format_id(self):
        self.order_type = self.format_id.order_type

    def ebics_upload(self):
        self.ensure_one()
        ctx = self._context.copy()
        ebics_file = self._ebics_upload()
        if ebics_file:
            ctx['ebics_file_id'] = ebics_file.id
        module = __name__.split('addons.')[1].split('.')[0]
        result_view = self.env.ref(
            '%s.ebics_xfer_view_form_result' % module)
        return {
            'name': _('EBICS file transfer result'),
            'res_id': self.id,
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'ebics.xfer',
            'view_id': result_view.id,
            'target': 'new',
            'context': ctx,
            'type': 'ir.actions.act_window',
        }

    def ebics_download(self):
        self.ensure_one()
        self.ebics_config_id._check_ebics_files()
        ctx = self._context.copy()
        self.note = ''
        client = self._setup_client()
        if client:
            download_formats = self.format_id \
                or self.ebics_config_id.ebics_file_format_ids.filtered(
                    lambda r: r.type == 'down')
            ebics_files = self.env['ebics.file']
            for df in download_formats:
                success = False
                order_type = df.order_type or 'FDL'
                params = {}
                if order_type == 'FDL':
                    params['filetype'] = df.name
                if order_type in ['FDL', 'C52', 'C53', 'C54']:
                    params.update({
                        'start':
                            self.date_from and self.date_from.isoformat()
                            or None,
                        'end':
                            self.date_to and self.date_to.isoformat()
                            or None,
                    })
                kwargs = {k: v for k, v in params.items() if v}
                try:
                    method = getattr(client, order_type)
                    data = method(**kwargs)
                    ebics_files += self._handle_download_data(data, df)
                    success = True
                except EbicsFunctionalError:
                    e = exc_info()
                    self.note += '\n'
                    self.note += _("EBICS Functional Error:")
                    self.note += '\n'
                    self.note += '%s (code: %s)' % (e[1].message, e[1].code)
                except EbicsTechnicalError:
                    e = exc_info()
                    self.note += '\n'
                    self.note += _("EBICS Technical Error:")
                    self.note += '\n'
                    self.note += '%s (code: %s)' % (e[1].message, e[1].code)
                except EbicsVerificationError:
                    self.note += '\n'
                    self.note += _("EBICS Verification Error:")
                    self.note += '\n'
                    self.note += _("The EBICS response could not be verified.")
                except UserError as e:
                    self.note += '\n'
                    self.note += _("Warning:")
                    self.note += '\n'
                    self.note += e.name
                except Exception:
                    self.note += '\n'
                    self.note += _("Unknown Error")
                    tb = ''.join(format_exception(*exc_info()))
                    self.note += '\n%s' % tb
                else:
                    # mark received data so that it is not included in further
                    # downloads
                    trans_id = client.last_trans_id
                    client.confirm_download(trans_id=trans_id, success=success)

            ctx['ebics_file_ids'] = ebics_files._ids

            if ebics_files:
                self.note += '\n'
                for f in ebics_files:
                    self.note += _(
                        "EBICS File '%s' is available for further processing."
                    ) % f.name
                    self.note += '\n'

        module = __name__.split('addons.')[1].split('.')[0]
        result_view = self.env.ref(
            '%s.ebics_xfer_view_form_result' % module)
        return {
            'name': _('EBICS file transfer result'),
            'res_id': self.id,
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'ebics.xfer',
            'view_id': result_view.id,
            'target': 'new',
            'context': ctx,
            'type': 'ir.actions.act_window',
        }

    def button_close(self):
        self.ensure_one()
        return {'type': 'ir.actions.act_window_close'}

    def view_ebics_file(self):
        self.ensure_one()
        module = __name__.split('addons.')[1].split('.')[0]
        act = self.env['ir.actions.act_window'].for_xml_id(
            module, 'ebics_file_action_download')
        act['domain'] = [('id', 'in', self._context['ebics_file_ids'])]
        return act

    def _ebics_upload(self):
        self.ensure_one()
        ebics_file = self.env['ebics.file']
        self.note = ''
        client = self._setup_client()
        if client:
            upload_data = base64.decodestring(self.upload_data)
            ef_format = self.format_id
            OrderID = False
            try:
                order_type = ef_format.order_type or 'FUL'
                method = hasattr(client, order_type) \
                    and getattr(client, order_type)
                if order_type == 'FUL':
                    kwargs = {}
                    bank = self.ebics_config_id.journal_ids[0].bank_id
                    cc = bank.country.code
                    if cc:
                        kwargs['country'] = cc
                    if self.test_mode:
                        kwargs['TEST'] = 'TRUE'
                    OrderID = method(ef_format.name, upload_data, **kwargs)
                elif order_type in ['CCT', 'CDD', 'CDB']:
                    OrderID = method(upload_data)
                elif order_type in ['XE2', 'XE3']:
                    OrderID = client.upload(order_type, upload_data)
                else:
                    # TODO: investigate if it makes sense to support
                    # a generic upload for a non-predefined order_type
                    pass
                if OrderID:
                    self.note += '\n'
                    self.note += _(
                        "EBICS File has been uploaded (OrderID %s)."
                    ) % OrderID
                    ef_note = _("EBICS OrderID: %s") % OrderID
                    if self.env.context.get('origin'):
                        ef_note += '\n' + _(
                            "Origin: %s") % self._context['origin']
                    suffix = self.format_id.suffix
                    fn = self.upload_fname
                    if not fn.endswith(suffix):
                        fn = '.'.join[fn, suffix]
                    ef_vals = {
                        'name': self.upload_fname,
                        'data': self.upload_data,
                        'date': fields.Datetime.now(),
                        'format_id': self.format_id.id,
                        'state': 'done',
                        'user_id': self._uid,
                        'ebics_userid_id': self.ebics_userid_id.id,
                        'note': ef_note,
                        'company_ids': [self.env.user.company_id.id],
                    }
                    self._update_ef_vals(ef_vals)
                    ebics_file = self.env['ebics.file'].create(ef_vals)

            except EbicsFunctionalError:
                e = exc_info()
                self.note += '\n'
                self.note += _("EBICS Functional Error:")
                self.note += '\n'
                self.note += '%s (code: %s)' % (e[1].message, e[1].code)
            except EbicsTechnicalError:
                e = exc_info()
                self.note += '\n'
                self.note += _("EBICS Technical Error:")
                self.note += '\n'
                self.note += '%s (code: %s)' % (e[1].message, e[1].code)
            except EbicsVerificationError:
                self.note += '\n'
                self.note += _("EBICS Verification Error:")
                self.note += '\n'
                self.note += _("The EBICS response could not be verified.")
            except Exception:
                self.note += '\n'
                self.note += _("Unknown Error")
                tb = ''.join(format_exception(*exc_info()))
                self.note += '\n%s' % tb

            if self.ebics_config_id.ebics_version == 'H003' and OrderID:
                self.ebics_config_id._update_order_number(OrderID)

        return ebics_file

    def _setup_client(self):
        self.ebics_config_id._check_ebics_keys()
        passphrase = self._get_passphrase()
        keyring = EbicsKeyRing(
            keys=self.ebics_userid_id.ebics_keys_fn,
            passphrase=passphrase)

        bank = EbicsBank(
            keyring=keyring,
            hostid=self.ebics_config_id.ebics_host,
            url=self.ebics_config_id.ebics_url)
        if self.ebics_config_id.ebics_version == 'H003':
            bank._order_number = self.ebics_config_id._get_order_number()

        user = EbicsUser(
            keyring=keyring,
            partnerid=self.ebics_config_id.ebics_partner,
            userid=self.ebics_userid_id.name)
        signature_class = self.format_id.signature_class \
            or self.ebics_userid_id.signature_class
        if signature_class == 'T':
            user.manual_approval = True

        try:
            client = EbicsClient(
                bank, user, version=self.ebics_config_id.ebics_version)
        except Exception:
            self.note += '\n'
            self.note += _("Unknown Error")
            tb = ''.join(format_exception(*exc_info()))
            self.note += '\n%s' % tb
            client = False

        return client

    def _get_passphrase(self):
        passphrase = self.ebics_userid_id.ebics_passphrase

        if passphrase:
            return passphrase

        module = __name__.split('addons.')[1].split('.')[0]
        passphrase_view = self.env.ref(
            '%s.ebics_xfer_view_form_passphrase' % module)
        return {
            'name': _('EBICS file transfer'),
            'res_id': self.id,
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'ebics.xfer',
            'view_id': passphrase_view.id,
            'target': 'new',
            'context': self._context,
            'type': 'ir.actions.act_window',
        }

    def _file_format_methods(self):
        """
        Extend this dictionary in order to add support
        for extra file formats.
        """
        res = {
            'camt.xxx.cfonb120.stm': self._handle_cfonb120,
            'camt.052.001.02.stm': self._handle_camt052,
            'camt.053.001.02.stm': self._handle_camt053,
        }
        return res

    def _update_ef_vals(self, ef_vals):
        """
        Adapt this method to customize the EBICS File values.
        """
        if self.format_id and self.format_id.type == 'up':
            fn = ef_vals['name']
            dups = self._check_duplicate_ebics_file(
                fn, self.format_id)
            if dups:
                n = 1
                fn = '_'.join([fn, str(n)])
                while self._check_duplicate_ebics_file(fn, self.format_id):
                    n += 1
                    fn = '_'.join([fn, str(n)])
                ef_vals['name'] = fn

    def _handle_download_data(self, data, file_format):
        ebics_files = self.env['ebics.file']
        if isinstance(data, dict):
            for doc in data:
                ebics_files += self._create_ebics_file(
                    data[doc], file_format, docname=doc)
        else:
            ebics_files += self._create_ebics_file(data, file_format)
        return ebics_files

    def _create_ebics_file(self, data, file_format, docname=None):
        """
        Write the data as received over the EBICS connection
        to a temporary file so that is is available for
        analysis (e.g. in case formats are received that cannot
        be handled in the current version of this module).

        TODO: add code to clean-up /tmp on a regular basis.

        After saving the data received we call the method to perform
        file format specific processing.
        """
        ebics_files_root = self.ebics_config_id.ebics_files
        tmp_dir = os.path.normpath(ebics_files_root + '/tmp')
        if not os.path.isdir(tmp_dir):
            os.makedirs(tmp_dir, mode=0o700)
        fn_parts = [self.ebics_config_id.ebics_host,
                    self.ebics_config_id.ebics_partner]
        if docname:
            fn_parts.append(docname)
        else:
            fn_date = self.date_to or fields.Date.today()
            fn_parts.append(fn_date.isoformat())
        base_fn = '_'.join(fn_parts)
        n = 1
        full_tmp_fn = os.path.normpath(tmp_dir + '/' + base_fn)
        while os.path.exists(full_tmp_fn):
            n += 1
            tmp_fn = base_fn + '_' + str(n).rjust(3, '0')
            full_tmp_fn = os.path.normpath(tmp_dir + '/' + tmp_fn)

        with open(full_tmp_fn, 'wb') as f:
            f.write(data)

        ff_methods = self._file_format_methods()
        if file_format.name in ff_methods:
            data = ff_methods[file_format.name](data)

        fn = '.'.join([base_fn, file_format.suffix])
        dups = self._check_duplicate_ebics_file(fn, file_format)
        if dups:
            raise UserError(_(
                "EBICS File with name '%s' has already been downloaded."
                "\nPlease check this file and rename in case there is "
                "no risk on duplicate transactions.")
                % fn)
        data = base64.encodestring(data)
        ef_vals = {
            'name': fn,
            'data': data,
            'date': fields.Datetime.now(),
            'date_from': self.date_from,
            'date_to': self.date_to,
            'format_id': file_format.id,
            'user_id': self._uid,
            'ebics_userid_id': self.ebics_userid_id.id,
            'company_ids': self.ebics_config_id.company_ids.ids,
        }
        self._update_ef_vals(ef_vals)
        ebics_file = self.env['ebics.file'].create(ef_vals)
        return ebics_file

    def _check_duplicate_ebics_file(self, fn, file_format):
        dups = self.env['ebics.file'].search(
            [('name', '=', fn),
             ('format_id', '=', file_format.id)])
        return dups

    def _detect_upload_format(self):
        """
        Use this method in order to automatically detect and set the
        EBICS upload file format.
        """
        pass

    def _update_order_number(self, OrderID):
        o_list = list(OrderID)
        for i, c in enumerate(reversed(o_list), start=1):
            if c == '9':
                o_list[-i] = 'A'
                break
            if c == 'Z':
                continue
            else:
                o_list[-i] = chr(ord(c) + 1)
                break
        next = ''.join(o_list)
        if next == 'ZZZZ':
            next = 'A000'
        self.ebics_config_id.order_number = next

    def _insert_line_terminator(self, data_in, line_len):
        data_in = data_in.replace(b'\n', b'').replace(b'\r', b'')
        data_out = b''
        max = len(data_in)
        i = 0
        while i + line_len <= max:
            data_out += data_in[i:i + line_len] + b'\n'
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
