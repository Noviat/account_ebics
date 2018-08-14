import logging

_logger = logging.getLogger(__name__)

try:
    from . import models
    from . import wizards
except Exception:
    _logger.warning("Import Error, check if fintech lib has been installed")
