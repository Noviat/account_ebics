# Copyright 2009-2019 Noviat.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    'name': 'Upload Payment Order via EBICS',
    'version': '11.0.1.0.0',
    'license': 'AGPL-3',
    'author': 'Noviat',
    'category': 'Accounting & Finance',
    'depends': [
        'account_ebics',
        'account_payment_order'],
    'data': [
        'views/account_payment_order.xml',
    ],
    'installable': True,
    "images": ["static/description/cover.png"],
}
