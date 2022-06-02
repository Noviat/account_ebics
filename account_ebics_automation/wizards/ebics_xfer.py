# © 2022 initOS GmbH
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models


class EbicsXfer(models.TransientModel):
    _inherit = "ebics.xfer"

    @api.model
    def download_by_date(self, config, date_from, date_to):
        wiz = self.create(
            {
                "ebics_config_id": config.id,
                "date_from": date_from,
                "date_to": date_to,
            }
        )

        # Automatically fill the other values
        wiz.with_context(ebics_download=True)._onchange_ebics_config_id()
        wiz.ebics_download()
