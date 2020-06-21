# Copyright 2009-2020 Noviat.
# License LGPL-3 or later (http://www.gnu.org/licenses/lpgl).

{
    'name': 'EBICS banking protocol',
    'version': '13.0.1.0.2',
    'license': 'LGPL-3',
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
    'external_dependencies': {
        'python': [
            'fintech',
            'cryptography',
            ]
        },
}
