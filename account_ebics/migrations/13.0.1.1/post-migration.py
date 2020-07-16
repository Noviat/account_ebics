# Copyright 2009-2020 Noviat.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from openupgradelib import openupgrade  # pylint: disable=W7936
import os


@openupgrade.migrate()
def migrate(env, version):

    _ebics_config_upgrade(env, version)
    _noupdate_changes(env, version)


def _ebics_config_upgrade(env, version):
    env.cr.execute("SELECT * FROM ebics_config")
    cfg_datas = env.cr.dictfetchall()
    for cfg_data in cfg_datas:
        cfg = env['ebics.config'].browse(cfg_data['id'])
        journal = env['account.journal'].search(
            [('bank_account_id', '=', cfg_data['bank_id'])])
        keys_fn_old = cfg_data['ebics_keys']
        ebics_keys_root = os.path.dirname(keys_fn_old)
        if os.path.isfile(keys_fn_old):
            keys_fn = ebics_keys_root + '/' + cfg_data['ebics_user'] + '_keys'
            os.rename(keys_fn_old, keys_fn)
        state = cfg_data['state'] == 'active' and 'confirm' or 'draft'
        cfg.write({
            'company_ids': [(6, 0, [cfg_data['company_id']])],
            'journal_ids': [(6, 0, [journal.id])],
            'ebics_keys': ebics_keys_root,
            'state': state,
        })

        user_vals = {
            'ebics_config_id': cfg_data['id'],
            'name': cfg_data['ebics_user'],
        }
        for fld in [
                'signature_class', 'ebics_passphrase',
                'ebics_ini_letter_fn', 'ebics_public_bank_keys_fn',
                'ebics_key_x509', 'ebics_key_x509_dn_cn',
                'ebics_key_x509_dn_o', 'ebics_key_x509_dn_ou',
                'ebics_key_x509_dn_c', 'ebics_key_x509_dn_st',
                'ebics_key_x509_dn_l', 'ebics_key_x509_dn_e',
                'ebics_file_format_ids', 'state']:
            if cfg_data.get(fld):
                if fld == 'ebics_file_format_ids':
                    user_vals[fld] = [(6, 0, cfg_data[fld])]
                elif fld == 'state' and cfg_data['state'] == 'active':
                    user_vals['state'] = 'active_keys'
                else:
                    user_vals[fld] = cfg_data[fld]
        ebics_userid = env['ebics.userid'].create(user_vals)
        env.cr.execute(
            """
            UPDATE ir_attachment
            SET res_model = 'ebics.userid', res_id = %s
            WHERE name in ('ebics_ini_letter', 'ebics_public_bank_keys');
            """
            % ebics_userid.id)

    if len(cfg_datas) == 1:
        env.cr.execute(
            "UPDATE ebics_file SET ebics_userid_id = %s" % ebics_userid.id)


def _noupdate_changes(env, version):
    openupgrade.load_data(
        env.cr,
        'account_ebics',
        'migrations/13.0.1.1/noupdate_changes.xml'
    )
