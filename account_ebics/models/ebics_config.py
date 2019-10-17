# Copyright 2009-2019 Noviat.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

"""
import logging
logging.basicConfig(
    level=logging.DEBUG,
    format='[%(asctime)s] %(levelname)s - %(name)s: %(message)s')
"""

import base64
import logging
import re
import os
from sys import exc_info
from urllib.error import URLError

from odoo import api, fields, models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

try:
    import fintech
    from fintech.ebics import EbicsKeyRing, EbicsBank, EbicsUser,\
        EbicsClient, EbicsFunctionalError, EbicsTechnicalError
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


class EbicsConfig(models.Model):
    """
    EBICS configuration is stored in a separate object in order to
    allow extra security policies on this object.

    Remark:
    This Configuration model implements a simple model of the relationship
    between users and authorizations and may need to be adapted
    in next versions of this module to cope with higher complexity .
    """
    _name = 'ebics.config'
    _description = 'EBICS Configuration'
    _order = 'name'

    name = fields.Char(string='Name', required=True)
    bank_id = fields.Many2one(
        comodel_name='res.partner.bank',
        readonly=True, states={'draft': [('readonly', False)]},
        string='Bank Account', required=True)
    ebics_host = fields.Char(
        string='EBICS HostID', required=True,
        readonly=True, states={'draft': [('readonly', False)]},
        help="Contact your bank to get the EBICS HostID."
             "\nIn France the BIC is usually allocated to the HostID "
             "whereas in Germany it tends to be an institute specific string "
             "of 8 characters.")
    ebics_url = fields.Char(
        string='EBICS URL', required=True,
        readonly=True, states={'draft': [('readonly', False)]},
        help="Contact your bank to get the EBICS URL.")
    ebics_version = fields.Selection(
        selection=[('H003', 'H003 (2.4)'),
                   ('H004', 'H004 (2.5)')],
        string='EBICS protocol version',
        readonly=True, states={'draft': [('readonly', False)]},
        required=True, default='H004')
    ebics_partner = fields.Char(
        string='EBICS PartnerID', required=True,
        readonly=True, states={'draft': [('readonly', False)]},
        help="Organizational unit (company or individual) "
             "that concludes a contract with the bank. "
             "\nIn this contract it will be agreed which order types "
             "(file formats) are used, which accounts are concerned, "
             "which of the customer's users (subscribers) "
             "communicate with the EBICS bank server and the authorisations "
             "that these users will possess. "
             "\nIt is identified by the PartnerID.")
    ebics_user = fields.Char(
        string='EBICS UserID', required=True,
        readonly=True, states={'draft': [('readonly', False)]},
        help="Human users or a technical system that is/are "
             "assigned to a customer. "
             "\nOn the EBICS bank server it is identified "
             "by the combination of UserID and PartnerID. "
             "The technical subscriber serves only for the data exchange "
             "between customer and financial institution. "
             "The human user also can authorise orders.")
    # Currently only a singe signature class per user is supported
    # Classes A and B are not yet supported.
    signature_class = fields.Selection(
        selection=[('E', 'Single signature'),
                   ('T', 'Transport signature')],
        string='Signature Class',
        required=True, default='T',
        readonly=True, states={'draft': [('readonly', False)]},
        help="Default signature class."
             "This default can be overriden for specific "
             "EBICS transactions (cf. File Formats).")
    ebics_files = fields.Char(
        string='EBICS Files Root', required=True,
        readonly=True, states={'draft': [('readonly', False)]},
        default=lambda self: self._default_ebics_files(),
        help="Root Directory for EBICS File Transfer Folders.")

    # We store the EBICS keys in a separate directory in the file system.
    # This directory requires special protection to reduce fraude.
    ebics_keys = fields.Char(
        string='EBICS Keys', required=True,
        readonly=True, states={'draft': [('readonly', False)]},
        default=lambda self: self._default_ebics_keys(),
        help="File holding the EBICS Keys."
             "\nSpecify the full path (directory + filename).")
    ebics_keys_found = fields.Boolean(
        compute='_compute_ebics_keys_found')
    ebics_passphrase = fields.Char(
        string='EBICS Passphrase')
    ebics_key_version = fields.Selection(
        selection=[('A005', 'A005 (RSASSA-PKCS1-v1_5)'),
                   ('A006', 'A006 (RSASSA-PSS)')],
        string='EBICS key version',
        default='A006',
        readonly=True, states={'draft': [('readonly', False)]},
        help="The key version of the electronic signature.")
    ebics_key_bitlength = fields.Integer(
        string='EBICS key bitlength',
        default=2048,
        readonly=True, states={'draft': [('readonly', False)]},
        help="The bit length of the generated keys. "
             "\nThe value must be between 1536 and 4096.")
    ebics_ini_letter = fields.Binary(
        string='EBICS INI Letter', readonly=True,
        help="INI-letter PDF document to be sent to your bank.")
    ebics_ini_letter_fn = fields.Char(
        string='INI-letter Filename', readonly=True)
    ebics_public_bank_keys = fields.Binary(
        string='EBICS Public Bank Keys', readonly=True,
        help="EBICS Public Bank Keys to be checked for consistency.")
    ebics_public_bank_keys_fn = fields.Char(
        string='EBICS Public Bank Keys Filename', readonly=True)

    # X.509 Distinguished Name attributes used to
    # create self-signed X.509 certificates
    ebics_key_x509 = fields.Boolean(
        string='X509 support',
        help="Set this flag in order to work with "
             "self-signed X.509 certificates")
    ebics_key_x509_dn_cn = fields.Char(
        string='Common Name [CN]',
        readonly=True, states={'draft': [('readonly', False)]},
    )
    ebics_key_x509_dn_o = fields.Char(
        string='Organization Name [O]',
        readonly=True, states={'draft': [('readonly', False)]},
    )
    ebics_key_x509_dn_ou = fields.Char(
        string='Organizational Unit Name [OU]',
        readonly=True, states={'draft': [('readonly', False)]},
    )
    ebics_key_x509_dn_c = fields.Char(
        string='Country Name [C]',
        readonly=True, states={'draft': [('readonly', False)]},
    )
    ebics_key_x509_dn_st = fields.Char(
        string='State Or Province Name [ST]',
        readonly=True, states={'draft': [('readonly', False)]},
    )
    ebics_key_x509_dn_l = fields.Char(
        string='Locality Name [L]',
        readonly=True, states={'draft': [('readonly', False)]},
    )
    ebics_key_x509_dn_e = fields.Char(
        string='Email Address',
        readonly=True, states={'draft': [('readonly', False)]},
    )
    ebics_file_format_ids = fields.Many2many(
        comodel_name='ebics.file.format',
        column1='config_id', column2='format_id',
        string='EBICS File Formats',
        readonly=True, states={'draft': [('readonly', False)]},
    )
    state = fields.Selection(
        [('draft', 'Draft'),
         ('init', 'Initialisation'),
         ('get_bank_keys', 'Get Keys from Bank'),
         ('to_verify', 'Verification'),
         ('active', 'Active')],
        string='State',
        default='draft',
        required=True, readonly=True)
    order_number = fields.Char(
        size=4, readonly=True, states={'draft': [('readonly', False)]},
        help="Specify the number for the next order."
             "\nThis number should match the following pattern : "
             "[A-Z]{1}[A-Z0-9]{3}")
    active = fields.Boolean(
        string='Active', default=True)
    company_id = fields.Many2one(
        'res.company', string='Company',
        default=lambda self: self.env.user.company_id,
        required=True)

    @api.model
    def _default_ebics_files(self):
        return '/'.join(['/home/odoo/ebics_files', self._cr.dbname])

    @api.model
    def _default_ebics_keys(self):
        return '/'.join(['/etc/odoo/ebics_keys',
                         self._cr.dbname,
                         'mykeys'])

    @api.multi
    @api.depends('ebics_keys')
    def _compute_ebics_keys_found(self):
        for cfg in self:
            cfg.ebics_keys_found = (
                cfg.ebics_keys and os.path.isfile(cfg.ebics_keys))

    @api.multi
    @api.constrains('order_number')
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
                raise UserError(_(
                    "Order Number should comply with the following pattern:"
                    "\n[A-Z]{1}[A-Z0-9]{3}"))

    @api.multi
    def unlink(self):
        for ebics_config in self:
            if ebics_config.state == 'active':
                raise UserError(_(
                    "You cannot remove active EBICS congirations."))
        return super(EbicsConfig, self).unlink()

    @api.multi
    def set_to_draft(self):
        return self.write({'state': 'draft'})

    @api.multi
    def set_to_get_bank_keys(self):
        return self.write({'state': 'get_bank_keys'})

    @api.multi
    def set_to_active(self):
        return self.write({'state': 'active'})

    @api.multi
    def ebics_init_1(self):
        """
        Initialization of bank keys - Step 1:
        Create new keys and certificates for this user
        """
        self.ensure_one()
        self._check_ebics_files()
        if self.state != 'draft':
            raise UserError(
                _("Set state to 'draft' before Bank Key (re)initialisation."))

        if not self.ebics_passphrase:
            raise UserError(
                _("Set a passphrase."))

        try:
            keyring = EbicsKeyRing(
                keys=self.ebics_keys,
                passphrase=self.ebics_passphrase)
            bank = EbicsBank(
                keyring=keyring, hostid=self.ebics_host, url=self.ebics_url)
            user = EbicsUser(
                keyring=keyring, partnerid=self.ebics_partner,
                userid=self.ebics_user)
        except Exception:
            exctype, value = exc_info()[:2]
            error = _("EBICS Initialisation Error:")
            error += '\n' + str(exctype) + '\n' + str(value)
            raise UserError(error)

        self._check_ebics_keys()
        if not os.path.isfile(self.ebics_keys):
            try:
                user.create_keys(
                    keyversion=self.ebics_key_version,
                    bitlength=self.ebics_key_bitlength)
            except Exception:
                exctype, value = exc_info()[:2]
                error = _("EBICS Initialisation Error:")
                error += '\n' + str(exctype) + '\n' + str(value)
                raise UserError(error)

        if self.ebics_key_x509:
            dn_attrs = {
                'commonName': self.ebics_key_x509_dn_cn,
                'organizationName': self.ebics_key_x509_dn_o,
                'organizationalUnitName': self.ebics_key_x509_dn_ou,
                'countryName': self.ebics_key_x509_dn_c,
                'stateOrProvinceName': self.ebics_key_x509_dn_st,
                'localityName': self.ebics_key_x509_dn_l,
                'emailAddress': self.ebics_key_x509_dn_e,
            }
            kwargs = {k: v for k, v in dn_attrs.items() if v}
            user.create_certificates(**kwargs)

        client = EbicsClient(bank, user, version=self.ebics_version)

        # Send the public electronic signature key to the bank.
        try:
            if self.ebics_version == 'H003':
                bank._order_number = self._get_order_number()
            OrderID = client.INI()
            _logger.info(
                '%s, EBICS INI command, OrderID=%s', self._name, OrderID)
            if self.ebics_version == 'H003':
                self._update_order_number(OrderID)
        except URLError:
            exctype, value = exc_info()[:2]
            raise UserError(_(
                "urlopen error:\n url '%s' - %s")
                % (self.ebics_url, str(value)))
        except EbicsFunctionalError:
            e = exc_info()
            error = _("EBICS Functional Error:")
            error += '\n'
            error += '%s (code: %s)' % (e[1].message, e[1].code)
            raise UserError(error)
        except EbicsTechnicalError:
            e = exc_info()
            error = _("EBICS Technical Error:")
            error += '\n'
            error += '%s (code: %s)' % (e[1].message, e[1].code)
            raise UserError(error)

        # Send the public authentication and encryption keys to the bank.
        if self.ebics_version == 'H003':
            bank._order_number = self._get_order_number()
        OrderID = client.HIA()
        _logger.info('%s, EBICS HIA command, OrderID=%s', self._name, OrderID)
        if self.ebics_version == 'H003':
            self._update_order_number(OrderID)

        # Create an INI-letter which must be printed and sent to the bank.
        cc = self.bank_id.bank_id.country.code
        if cc in ['FR', 'DE']:
            lang = cc
        else:
            lang = self.env.user.lang or \
                self.env['res.lang'].search([])[0].code
            lang = lang[:2]
        tmp_dir = os.path.normpath(self.ebics_files + '/tmp')
        if not os.path.isdir(tmp_dir):
            os.makedirs(tmp_dir, mode=0o700)
        fn_date = fields.Date.today().isoformat()
        fn = '_'.join([self.ebics_host, 'ini_letter', fn_date]) + '.pdf'
        full_tmp_fn = os.path.normpath(tmp_dir + '/' + fn)
        user.create_ini_letter(
            bankname=self.bank_id.bank_id.name,
            path=full_tmp_fn,
            lang=lang)
        with open(full_tmp_fn, 'rb') as f:
            letter = f.read()
            self.write({
                'ebics_ini_letter': base64.encodestring(letter),
                'ebics_ini_letter_fn': fn,
            })

        return self.write({'state': 'init'})

    @api.multi
    def ebics_init_2(self):
        """
        Initialization of bank keys - Step 2:
        Activation of the account by the bank.
        """
        if self.state != 'init':
            raise UserError(
                _("Set state to 'Initialisation'."))
        self.ensure_one()
        return self.write({'state': 'get_bank_keys'})

    @api.multi
    def ebics_init_3(self):
        """
        Initialization of bank keys - Step 3:

        After the account has been activated the public bank keys
        must be downloaded and checked for consistency.
        """
        self.ensure_one()
        self._check_ebics_files()
        if self.state != 'get_bank_keys':
            raise UserError(
                _("Set state to 'Get Keys from Bank'."))
        keyring = EbicsKeyRing(
            keys=self.ebics_keys, passphrase=self.ebics_passphrase)
        bank = EbicsBank(
            keyring=keyring, hostid=self.ebics_host, url=self.ebics_url)
        user = EbicsUser(
            keyring=keyring, partnerid=self.ebics_partner,
            userid=self.ebics_user)
        client = EbicsClient(
            bank, user, version=self.ebics_version)

        public_bank_keys = client.HPB()
        public_bank_keys = public_bank_keys.encode()
        tmp_dir = os.path.normpath(self.ebics_files + '/tmp')
        if not os.path.isdir(tmp_dir):
            os.makedirs(tmp_dir, mode=0o700)
        fn_date = fields.Date.today().isoformat()
        fn = '_'.join([self.ebics_host, 'public_bank_keys', fn_date]) + '.txt'
        self.write({
            'ebics_public_bank_keys': base64.encodestring(public_bank_keys),
            'ebics_public_bank_keys_fn': fn,
            'state': 'to_verify',
        })

        return True

    @api.multi
    def ebics_init_4(self):
        """
        Initialization of bank keys - Step 2:
        Confirm Verification of the public bank keys
        and activate the bank keyu.
        """
        self.ensure_one()
        if self.state != 'to_verify':
            raise UserError(
                _("Set state to 'Verification'."))

        keyring = EbicsKeyRing(
            keys=self.ebics_keys, passphrase=self.ebics_passphrase)
        bank = EbicsBank(
            keyring=keyring, hostid=self.ebics_host, url=self.ebics_url)
        bank.activate_keys()
        return self.write({'state': 'active'})

    @api.multi
    def change_passphrase(self):
        self.ensure_one()
        ctx = dict(self._context, default_ebics_config_id=self.id)
        module = __name__.split('addons.')[1].split('.')[0]
        view = self.env.ref(
            '%s.ebics_change_passphrase_view_form' % module)
        return {
            'name': _('EBICS keys change passphrase'),
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'ebics.change.passphrase',
            'view_id': view.id,
            'target': 'new',
            'context': ctx,
            'type': 'ir.actions.act_window',
        }

    def _get_order_number(self):
        return self.order_number

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
        self.order_number = next

    def _check_ebics_keys(self):
        if self.ebics_keys:
            dirname = os.path.dirname(self.ebics_keys)
            if not os.path.exists(dirname):
                raise UserError(_(
                    "EBICS Keys Directory '%s' is not available."
                    "\nPlease contact your system administrator.")
                    % dirname)
        if os.path.isdir(self.ebics_keys):
            raise UserError(_(
                "Configuration Error.\n"
                "The 'EBICS Keys' parameter should be a full path "
                "(directory + filename) not a directory name."))

    def _check_ebics_files(self):
        dirname = self.ebics_files or ''
        if not os.path.exists(dirname):
            raise UserError(_(
                "EBICS Files Root Directory %s is not available."
                "\nPlease contact your system administrator.")
                % dirname)
