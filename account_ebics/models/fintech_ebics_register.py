# Copyright 2009-2020 Noviat.
# License LGPL-3 or later (http://www.gnu.org/licenses/lpgl).

import logging
from sys import exc_info
from traceback import format_exception

from odoo.tools import config

_logger = logging.getLogger(__name__)

try:
    import fintech
except ImportError:
    fintech = None
    _logger.warning('Failed to import fintech')

fintech_register_name = config.get('fintech_register_name')
fintech_register_keycode = config.get('fintech_register_keycode')
fintech_register_users = config.get('fintech_register_users')

try:
    if fintech:
        fintech_register_users = fintech_register_users \
            and [x.strip() for x in fintech_register_users.split(',')]
        fintech.cryptolib = 'cryptography'
        fintech.register(
            fintech_register_name,
            fintech_register_keycode,
            fintech_register_users)
except RuntimeError as e:
    if e.message == "'register' can be called only once":
        pass
    else:
        _logger.error(e.message)
        fintech.register()
except Exception:
    msg = "fintech.register error"
    tb = ''.join(format_exception(*exc_info()))
    msg += '\n%s' % tb
    _logger.error(msg)
    fintech.register()
