# Copyright 2009-2023 Noviat.
# License AGPL-3 or later (http://www.gnu.org/licenses/agpl).

import logging
from sys import exc_info
from traceback import format_exception

from odoo.tools import config

_logger = logging.getLogger(__name__)

try:
    import fintech
except ImportError:
    fintech = None
    _logger.warning("Failed to import fintech")

fintech_register_name = config.get("fintech_register_name")
fintech_register_keycode = config.get("fintech_register_keycode")
fintech_register_users = config.get("fintech_register_users")

try:
    if fintech:
        fintech_register_users = (
            fintech_register_users
            and [x.strip() for x in fintech_register_users.split(",")]
            or None
        )
        fintech.cryptolib = "cryptography"
        fintech.register(
            name=fintech_register_name,
            keycode=fintech_register_keycode,
            users=fintech_register_users,
        )
except RuntimeError as e:
    if str(e) == "'register' can be called only once":
        pass
    else:
        _logger.error(str(e))
        fintech.register()
except Exception:
    msg = "fintech.register error"
    tb = "".join(format_exception(*exc_info()))
    msg += "\n%s" % tb
    _logger.error(msg)
    fintech.register()
