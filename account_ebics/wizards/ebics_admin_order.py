# Copyright 2024 Noviat.
# License LGPL-3 or later (https://www.gnu.org/licenses/lgpl).

import logging
import pprint

from odoo import api, fields, models

_logger = logging.getLogger(__name__)

try:
    from fintech.ebics import EbicsTechnicalError
except ImportError:
    _logger.warning("Failed to import fintech")


class EbicsAdminOrder(models.TransientModel):
    _inherit = "ebics.xfer"
    _name = "ebics.admin.order"
    _description = "EBICS Administrative Order"

    admin_order_type = fields.Selection(
        selection=lambda self: self._selection_admin_order_type(),
        string="Order",
    )

    @api.model
    def _selection_admin_order_type(self):
        return [
            ("HAA", "HAA - Business transaction formats BTF"),
            ("HPD", "HPD - Bank parameters"),
            ("HKD", "HKD - Subscriber information"),
            ("HTD", "HTD - Customer properties and settings"),
        ]

    def ebics_admin_order(self):
        self.ensure_one()
        client = self._setup_client()
        if not client:
            self.note += (
                self.env._("EBICS client setup failed for connection '%s'")
                % self.ebics_config_id.name
            )
        else:
            try:
                data = getattr(client, self.admin_order_type)(parsed=True)
                pp = pprint.PrettyPrinter()
                self.note = pp.pformat(data)
            except EbicsTechnicalError as e:
                self.note = "\n"
                self.note += self.env._(
                    "EBICS Technical Error during execution of order %(order_type)s:",
                    order_type=self.admin_order_type,
                )
                self.note += "\n"
                self.note += f"{e.message} (code: {e.code})"
        module = __name__.split("addons.")[1].split(".")[0]
        result_view = self.env.ref(f"{module}.ebics_admin_order_view_form_result")
        return {
            "name": self.env._("EBICS Administrative Order result"),
            "res_id": self.id,
            "view_mode": "form",
            "res_model": "ebics.admin.order",
            "view_id": result_view.id,
            "target": "new",
            "context": self.env.context,
            "type": "ir.actions.act_window",
        }
