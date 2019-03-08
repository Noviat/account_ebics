# Copyright 2009-2019 Noviat.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import logging

from odoo import api, fields, models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class EbicsFile(models.Model):
    _name = 'ebics.file'
    _description = 'Object to store EBICS Data Files'
    _order = 'date desc'

    name = fields.Char(string='Filename')
    data = fields.Binary(string='File', readonly=True)
    format_id = fields.Many2one(
        comodel_name='ebics.file.format',
        string='EBICS File Formats',
        readonly=True)
    type = fields.Selection(
        related='format_id.type',
        readonly=True)
    date_from = fields.Date(
        readonly=True,
        help="'Date From' as entered in the download wizard.")
    date_to = fields.Date(
        readonly=True,
        help="'Date To' as entered in the download wizard.")
    date = fields.Datetime(
        required=True, readonly=True,
        help='File Upload/Download date')
    bank_statement_ids = fields.One2many(
        comodel_name='account.bank.statement',
        inverse_name='ebics_file_id',
        string='Generated Bank Statements', readonly=True)
    state = fields.Selection(
        [('draft', 'Draft'),
         ('done', 'Done')],
        string='State',
        default='draft',
        required=True, readonly=True)
    user_id = fields.Many2one(
        comodel_name='res.users', string='User',
        default=lambda self: self.env.user,
        readonly=True)
    note = fields.Text(string='Notes')
    note_process = fields.Text(string='Notes')
    company_id = fields.Many2one(
        comodel_name='res.company',
        string='Company',
        default=lambda self: self._default_company_id())

    _sql_constraints = [
        ('name_company_uniq', 'unique (name, company_id, format_id)',
         'This File has already been imported !')
    ]

    @api.model
    def _default_company_id(self):
        """
        Adapt this method in case your bank provides transactions
        of multiple legal entities in a single EBICS File.
        """
        return self.env.user.company_id

    @api.multi
    def unlink(self):
        ff_methods = self._file_format_methods()
        for ebics_file in self:
            if ebics_file.state == 'done':
                raise UserError(_(
                    "You can only remove EBICS files in state 'Draft'."))
            # execute format specific actions
            ff = ebics_file.format_id.name
            if ff in ff_methods:
                if ff_methods[ff].get('unlink'):
                    ff_methods[ff]['unlink'](ebics_file)
            # remove bank statements
            ebics_file.bank_statement_ids.unlink()
        return super(EbicsFile, self).unlink()

    @api.multi
    def set_to_draft(self):
        return self.write({'state': 'draft'})

    @api.multi
    def set_to_done(self):
        return self.write({'state': 'done'})

    @api.multi
    def process(self):
        self.ensure_one()
        self.note_process = ''
        ff_methods = self._file_format_methods()
        ff = self.format_id.name
        if ff in ff_methods:
            if ff_methods[ff].get('process'):
                res = ff_methods[ff]['process'](self)
                self.state = 'done'
                return res
        else:
            return self._process_undefined_format()

    @api.multi
    def action_open_bank_statements(self):
        self.ensure_one()
        action = self.env['ir.actions.act_window'].for_xml_id(
            'account', 'action_bank_statement_tree')
        domain = eval(action.get('domain') or '[]')
        domain += [('id', 'in', self._context.get('statement_ids'))]
        action.update({'domain': domain})
        return action

    @api.multi
    def button_close(self):
        self.ensure_one()
        return {'type': 'ir.actions.act_window_close'}

    def _file_format_methods(self):
        """
        Extend this dictionary in order to add support
        for extra file formats.
        """
        res = {
            'camt.xxx.cfonb120.stm':
                {'process': self._process_cfonb120,
                 'unlink': self._unlink_cfonb120},
            'camt.053.001.02.stm':
                {'process': self._process_camt053,
                 'unlink': self._unlink_camt053},
        }
        return res

    def _check_import_module(self, module):
        mod = self.env['ir.module.module'].search(
            [('name', '=like', module),
             ('state', '=', 'installed')])
        if not mod:
            raise UserError(_(
                "The module to process the '%s' format is not installed "
                "on your system. "
                "\nPlease install module '%s'")
                % (self.format_id.name, module))

    def _process_result_action(self, ctx):
        module = __name__.split('addons.')[1].split('.')[0]
        result_view = self.env.ref('%s.ebics_file_view_form_result' % module)
        return {
            'name': _('Import EBICS File'),
            'res_id': self.id,
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': self._name,
            'view_id': result_view.id,
            'target': 'new',
            'context': ctx,
            'type': 'ir.actions.act_window',
        }

    @staticmethod
    def _process_cfonb120(self):
        """
        TODO:
        adapt OCA import logic to find correct journal on the basis
        of both account number and currency.
        Prompt for journal in case the journal is not found.
        """
        import_module = 'account_bank_statement_import_fr_cfonb'
        self._check_import_module(import_module)
        wiz_model = 'account.bank.statement.import'
        wiz_vals = {'data_file': self.data}
        wiz = self.env[wiz_model].create(wiz_vals)
        res = wiz.import_file()
        notifications = []
        statement_ids = []
        if res.get('context'):
            notifications = res['context'].get('notifications', [])
            statement_ids = res['context'].get('statement_ids', [])
        if notifications:
            for notif in notifications:
                parts = []
                for k in ['type', 'message', 'details']:
                    if notif.get(k):
                        msg = '%s: %s' % (k, notif[k])
                        parts.append(msg)
                self.note_process += '\n'.join(parts)
                self.note_process += '\n'
            self.note_process += '\n'
        self.note_process += _(
            "Number of Bank Statements: %s"
        ) % len(statement_ids)
        if statement_ids:
            self.bank_statement_ids = [(6, 0, statement_ids)]
        ctx = dict(self._context, statement_ids=statement_ids)
        return self._process_result_action(ctx)

    @staticmethod
    def _unlink_cfonb120(self):
        """
        Placeholder for cfonb120 specific actions before removing the
        EBICS data file and its related bank statements.
        """
        pass

    @staticmethod
    def _process_camt053(self):
        import_module = 'account_bank_statement_import_camt%'
        self._check_import_module(import_module)
        wiz_model = 'account.bank.statement.import'
        wiz_vals = {
            'data_file': self.data,
            'filename': self.name,
        }
        ctx = dict(self.env.context, active_model='ebics.file')
        wiz = self.env[wiz_model].with_context(ctx).create(wiz_vals)
        res = wiz.import_file()
        if res.get('res_model') \
                == 'account.bank.statement.import.journal.creation':
            if res.get('context'):
                bank_account = res['context'].get('default_bank_acc_number')
                raise UserError(_(
                    "No financial journal found for Company Bank Account %s"
                ) % bank_account)
        notifications = []
        statement_ids = []
        if res.get('context'):
            notifications = res['context'].get('notifications', [])
            statement_ids = res['context'].get('statement_ids', [])
        if notifications:
            for notif in notifications:
                parts = []
                for k in ['type', 'message', 'details']:
                    if notif.get(k):
                        msg = '%s: %s' % (k, notif[k])
                        parts.append(msg)
                self.note_process += '\n'.join(parts)
                self.note_process += '\n'
            self.note_process += '\n'
        self.note_process += _(
            "Number of Bank Statements: %s"
        ) % len(statement_ids)
        if statement_ids:
            self.bank_statement_ids = [(6, 0, statement_ids)]
        ctx = dict(self._context, statement_ids=statement_ids)
        return self._process_result_action(ctx)

    @staticmethod
    def _unlink_camt053(self):
        """
        Placeholder for camt053 specific actions before removing the
        EBICS data file and its related bank statements.
        """
        pass

    def _process_undefined_format(self):
        raise UserError(_(
            "The current version of the 'account_ebics' module "
            "has no support to automatically process EBICS files "
            "with format %s."
        ) % self.format_id.name)
