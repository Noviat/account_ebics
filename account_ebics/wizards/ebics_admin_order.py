# Copyright 2009-2023 Noviat.
# License LGPL-3 or later (http://www.gnu.org/licenses/lgpl).

import pprint

from odoo import _, api, fields, models


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
                _("EBICS client setup failed for connection '%s'")
                % self.ebics_config_id.name
            )
        else:
            data = getattr(client, self.admin_order_type)(parsed=True)
            pp = pprint.PrettyPrinter()
            self.note = pp.pformat(data)
        module = __name__.split("addons.")[1].split(".")[0]
        result_view = self.env.ref("%s.ebics_admin_order_view_form_result" % module)
        return {
            "name": _("EBICS Administrative Order result"),
            "res_id": self.id,
            "view_type": "form",
            "view_mode": "form",
            "res_model": "ebics.admin.order",
            "view_id": result_view.id,
            "target": "new",
            "context": self.env.context,
            "type": "ir.actions.act_window",
        }
