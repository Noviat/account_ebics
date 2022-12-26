# Copyright 2009-2022 Noviat.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    'name': 'EBICS banking protocol',
    'version': '11.0.1.8.0',
    'license': 'AGPL-3',
    'author': 'Noviat',
    'category': 'Accounting & Finance',
    'depends': ['account'],
    'data': [
        'security/ebics_security.xml',
        'security/ir.model.access.csv',
        'data/ebics_file_format.xml',
        'views/menuitem.xml',
        'views/ebics_config.xml',
        'views/ebics_file.xml',
        'views/ebics_file_format.xml',
        'wizard/ebics_change_passphrase.xml',
        'wizard/ebics_xfer.xml',
    ],
    'installable': True,
    'application': True,
}
