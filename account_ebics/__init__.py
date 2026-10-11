import functools
import logging

from odoo import api

_logger = logging.getLogger(__name__)

try:
    from . import models
    from . import wizards
except Exception:
    _logger.warning("Import Error, check if fintech lib has been installed")


@functools.cached_property
def neutralized(self):
    return bool(
        self["ir.config_parameter"].sudo().get_param("database.is_neutralized")
        or self["ir.ui.view"]
        .sudo()
        .search_count(
            [
                ("key", "in", ("web.neutralize_banner", "website.neutralize_ribbon")),
                ("active", "=", True),
            ]
        )
    )


api.Environment.neutralized = neutralized
neutralized.__set_name__(api.Environment, "neutralized")
