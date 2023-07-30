# Copyright 2009-2023 Noviat.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from sys import exc_info
from traceback import format_exception

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class EbicsBatchLog(models.Model):
    _name = "ebics.batch.log"
    _description = "Object to store EBICS Batch Import Logs"
    _order = "create_date desc"

    date_from = fields.Date()
    date_to = fields.Date()
    ebics_config_ids = fields.Many2many(
        comodel_name="ebics.config", string="EBICS Configurations"
    )
    log_ids = fields.One2many(
        comodel_name="ebics.batch.log.item",
        inverse_name="log_id",
        string="Batch Import Log Items",
        readonly=True,
    )
    file_ids = fields.Many2many(
        comodel_name="ebics.file",
        string="Batch Import EBICS Files",
        readonly=True,
    )
    file_count = fields.Integer(
        string="EBICS Files Count", compute="_compute_ebics_files_fields", readonly=True
    )
    has_draft_files = fields.Boolean(compute="_compute_ebics_files_fields")
    state = fields.Selection(
        selection=[("draft", "Draft"), ("error", "Error"), ("done", "Done")],
        required=True,
        readonly=True,
        default="draft",
    )

    @api.depends("file_ids")
    def _compute_ebics_files_fields(self):
        for rec in self:
            rec.has_draft_files = "draft" in rec.file_ids.mapped("state")
            rec.file_count = len(rec.file_ids)

    def unlink(self):
        for log in self:
            if log.state != "draft":
                raise UserError(_("Only log objects in state 'draft' can be deleted !"))
        return super().unlink()

    def button_draft(self):
        self.state = "draft"

    def button_done(self):
        self.state = "done"

    def reprocess(self):
        import_dict = {"errors": []}
        self._ebics_process(import_dict)
        self._finalise_processing(import_dict)

    def view_ebics_files(self):
        action = self.env["ir.actions.actions"]._for_xml_id(
            "account_ebics.ebics_file_action_download"
        )
        action["domain"] = [("id", "in", self.file_ids.ids)]
        return action

    def _batch_import(self, ebics_config_ids=None, date_from=None, date_to=None):
        """
        Call this method from a cron job to automate the EBICS import.
        """
        log_model = self.env["ebics.batch.log"]
        import_dict = {"errors": []}
        configs = self.env["ebics.config"].browse(ebics_config_ids) or self.env[
            "ebics.config"
        ].search(
            [
                ("company_ids", "in", self.env.user.company_ids.ids),
                ("state", "=", "confirm"),
            ]
        )
        log = log_model.create(
            {
                "ebics_config_ids": [(6, 0, configs.ids)],
                "date_from": date_from,
                "date_to": date_to,
            }
        )
        ebics_file_ids = []
        for config in configs:
            err_msg = (
                _("Error while processing EBICS connection '%s' :\n") % config.name
            )
            if config.state == "draft":
                import_dict["errors"].append(
                    err_msg
                    + _(
                        "Please set state to 'Confirm' and "
                        "Reprocess this EBICS Import Log."
                    )
                )
                continue
            if not any(config.mapped("ebics_userid_ids.ebics_passphrase_store")):
                import_dict["errors"].append(
                    err_msg
                    + _(
                        "No EBICS UserID with stored passphrase found.\n"
                        "You should configure such a UserID for automated downloads."
                    )
                )
                continue
            try:
                with self.env.cr.savepoint():
                    ebics_file_ids += self._ebics_import(
                        config, date_from, date_to, import_dict
                    )
            except UserError as e:
                import_dict["errors"].append(err_msg + " ".join(e.args))
            except Exception:
                tb = "".join(format_exception(*exc_info()))
                import_dict["errors"].append(err_msg + tb)
        log.file_ids = [(6, 0, ebics_file_ids)]
        try:
            log._ebics_process(import_dict)
        except UserError as e:
            import_dict["errors"].append(err_msg + " ".join(e.args))
        except Exception:
            tb = "".join(format_exception(*exc_info()))
            import_dict["errors"].append(err_msg + tb)
        log._finalise_processing(import_dict)

    def _finalise_processing(self, import_dict):
        log_item_model = self.env["ebics.batch.log.item"]
        state = self.has_draft_files and "draft" or "done"
        note = ""
        error_count = 0
        if import_dict["errors"]:
            state = "error"
            note = "\n\n".join(import_dict["errors"])
            error_count = len(import_dict["errors"])
        log_item_model.create(
            {
                "log_id": self.id,
                "state": state,
                "note": note,
                "error_count": error_count,
            }
        )
        self.state = state

    def _ebics_import(self, config, date_from, date_to, import_dict):
        ebics_userids = config.ebics_userid_ids.filtered(
            lambda r: r.ebics_passphrase_store
        )
        t_userids = ebics_userids.filtered(lambda r: r.signature_class == "T")
        ebics_userid = t_userids and t_userids[0] or ebics_userids[0]
        xfer_wiz = (
            self.env["ebics.xfer"]
            .with_context(ebics_download=True)
            .create(
                {
                    "ebics_config_id": config.id,
                    "date_from": date_from,
                    "date_to": date_to,
                }
            )
        )
        xfer_wiz._onchange_ebics_config_id()
        xfer_wiz.ebics_userid_id = ebics_userid
        res = xfer_wiz.ebics_download()
        file_ids = res["context"].get("ebics_file_ids", [])
        if res["context"]["err_cnt"]:
            import_dict["errors"].append(xfer_wiz.note)
        return file_ids

    def _ebics_process(self, import_dict):
        to_process = self.file_ids.filtered(lambda r: r.state == "draft")
        for ebics_file in to_process:
            ebics_file.process()


class EbicsBatchLogItem(models.Model):
    _name = "ebics.batch.log.item"
    _description = "Object to store EBICS Batch Import Log Items"
    _order = "create_date desc"

    log_id = fields.Many2one(
        comodel_name="ebics.batch.log",
        string="Batch Object",
        ondelete="cascade",
        readonly=True,
    )
    state = fields.Selection(
        selection=[("draft", "Draft"), ("error", "Error"), ("done", "Done")],
        required=True,
        readonly=True,
    )
    note = fields.Text(string="Batch Import Log", readonly=True)
    error_count = fields.Integer(string="Number of Errors", required=True, default=0)
