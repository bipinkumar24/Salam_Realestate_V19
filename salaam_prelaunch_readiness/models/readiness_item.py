# -*- coding: utf-8 -*-
"""
Pre-Launch Readiness Item - the 110 line records.

Each item maps to a row from the source Excel. The ``linked_record_ref``
Reference field is the integration backbone: items resolve to actual
records in the other Salaam modules (the ITP, the contract, the HSE
plan, the fatwa, etc.) rather than free-text status only.
"""
from odoo import api, fields, models, _
from odoo.exceptions import UserError


# Whitelist of models that an item may reference. Loose mode (per the
# v1 design decision): any of these is acceptable. v1.1 may tighten to
# a per-item allowed set.
LINKED_REF_WHITELIST = [
    # Execution / governance
    "salaam.decision.gate",
    "salaam.execution.decision.gate",
    "salaam.execution.plan.lot",
    "salaam.execution.plan.subpackage",
    "salaam.execution.plan.long.lead",
    "salaam.execution.plan.ve.session",
    # PM / QC office
    "salaam.pm.qc.itp",
    "salaam.pm.qc.itr",
    "salaam.pm.qc.material.submittal",
    "salaam.pm.qc.material.test",
    "salaam.pm.qc.commissioning",
    "salaam.pm.qc.concession",
    "salaam.pm.qc.witness.notification",
    "salaam.pm.qc.cri",
    "salaam.pm.qc.site.diary",
    # HSE
    "salaam.hse.plan",
    "salaam.hse.induction",
    "salaam.hse.incident",
    # Contracts / finance
    "salaam.dev.contract",
    "salaam.dev.contract.istisna",
    "salaam.dev.contract.mudaraba",
    "salaam.dev.contract.wakala",
    "salaam.dev.contract.murabaha",
    "salaam.dev.contract.spa",
    # Procurement / contractors
    "salaam.procurement.order",
    "salaam.procurement.long.lead",
    "salaam.contractor",
    "salaam.contractor.tier",
    "salaam.contractor.subcontract",
    # Reservation / sales
    "salaam.reservation",
    "salaam.reservation.batch",
    "crm.lead",
    # IAFAO
    "salaam.iafao.kpi",
    # Generic Odoo
    "documents.document",
    "ir.attachment",
    "project.task",
    "res.partner",
]


class ReadinessItem(models.Model):
    _name = "salaam.readiness.item"
    _description = "Salaam Pre-Launch Readiness Item"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "category_id, sequence, id"

    category_id = fields.Many2one(
        "salaam.readiness.category",
        string="Category",
        required=True,
        ondelete="cascade",
        index=True,
    )
    tracker_id = fields.Many2one(
        "salaam.readiness.tracker",
        string="Tracker",
        related="category_id.tracker_id",
        store=True,
        index=True,
    )
    sequence = fields.Integer(string="#", default=10)
    name = fields.Char(string="Item", required=True, translate=True, tracking=True)

    gate_type = fields.Selection(
        related="category_id.gate_type",
        string="Gate Type",
        store=True,
        readonly=True,
    )
    category_code = fields.Char(
        related="category_id.code",
        string="Cat",
        store=True,
        readonly=True,
    )

    owner_id = fields.Many2one(
        "res.users",
        string="Owner",
        tracking=True,
        help="Person accountable for completing this readiness item.",
    )
    due_date = fields.Date(string="Due Date", tracking=True)

    status = fields.Selection(
        [
            ("not_started", "Not Started"),
            ("in_progress", "In Progress"),
            ("done", "Done"),
            ("blocked", "Blocked"),
            ("na", "N/A"),
        ],
        string="Status",
        default="not_started",
        required=True,
        tracking=True,
    )

    pct_complete = fields.Float(
        string="% Complete",
        digits=(5, 2),
        compute="_compute_pct",
        store=True,
        readonly=False,
        tracking=True,
        help="Auto-set to 100 when status is Done, 0 when Blocked or "
             "Not Started. Free between 0-100 when In Progress.",
    )

    evidence_url = fields.Char(
        string="Evidence Link",
        help="External link (Drive, Dropbox, SharePoint) supporting "
             "the status of this item.",
    )
    evidence_attachment_ids = fields.Many2many(
        "ir.attachment",
        "salaam_readiness_item_attachment_rel",
        "item_id",
        "attachment_id",
        string="Evidence Files",
    )
    evidence_count = fields.Integer(
        string="Evidence",
        compute="_compute_evidence_count",
    )

    linked_record_ref = fields.Reference(
        selection="_selection_linked_models",
        string="Linked Record",
        help="The source-of-truth record in another Salaam module that "
             "evidences this readiness item (an ITP, a contract, an HSE "
             "plan, a fatwa, etc).",
    )

    notes = fields.Text(string="Notes")

    is_overdue = fields.Boolean(
        string="Overdue",
        compute="_compute_is_overdue",
        store=True,
    )
    is_blocked = fields.Boolean(
        string="Is Blocked",
        compute="_compute_is_blocked",
        store=True,
    )

    color = fields.Integer(
        string="Color",
        compute="_compute_color",
        help="Kanban color index.",
    )

    # ----- Selection helper for Reference field --------------------------
    @api.model
    def _selection_linked_models(self):
        """Return only models that exist in the current database."""
        return [
            (m, self.env[m]._description or m)
            for m in LINKED_REF_WHITELIST
            if m in self.env
        ] or [("ir.attachment", "Attachment")]

    # ----- Computes -------------------------------------------------------
    @api.depends("status")
    def _compute_pct(self):
        for rec in self:
            if rec.status == "done":
                rec.pct_complete = 100.0
            elif rec.status in ("not_started", "blocked"):
                rec.pct_complete = 0.0
            elif rec.status == "na":
                rec.pct_complete = 0.0
            # 'in_progress' keeps whatever value the user typed; if the
            # field was never set, default to 0
            elif not rec.pct_complete:
                rec.pct_complete = 0.0

    @api.depends("due_date", "status")
    def _compute_is_overdue(self):
        today = fields.Date.context_today(self)
        for rec in self:
            rec.is_overdue = bool(
                rec.due_date
                and rec.due_date < today
                and rec.status not in ("done", "na")
            )

    @api.depends("status")
    def _compute_is_blocked(self):
        for rec in self:
            rec.is_blocked = rec.status == "blocked"

    @api.depends("status", "is_overdue")
    def _compute_color(self):
        # Odoo kanban color codes: 0 default, 1 red, 2 orange, 3 yellow,
        # 4 light blue, 5 dark purple, 6 magenta, 7 cyan, 8 dark blue,
        # 9 fuchsia, 10 green, 11 violet
        for rec in self:
            if rec.status == "blocked":
                rec.color = 1   # red
            elif rec.status == "done":
                rec.color = 10  # green
            elif rec.is_overdue:
                rec.color = 2   # orange
            elif rec.status == "in_progress":
                rec.color = 4   # light blue
            elif rec.status == "na":
                rec.color = 0
            else:
                rec.color = 0

    @api.depends("evidence_attachment_ids")
    def _compute_evidence_count(self):
        for rec in self:
            rec.evidence_count = len(rec.evidence_attachment_ids)

    # ----- Constraints / hooks -------------------------------------------
    @api.constrains("pct_complete")
    def _check_pct_range(self):
        for rec in self:
            if rec.pct_complete < 0.0 or rec.pct_complete > 100.0:
                raise UserError(_("% Complete must be between 0 and 100."))

    @api.constrains("status", "tracker_id")
    def _check_locked_state(self):
        # Manager group can force edits with context flag (used by the
        # tracker's Reset to Draft flow). Officers and users get blocked.
        bypass = self.env.context.get("salaam_readiness_force_edit")
        is_manager = self.env.user.has_group(
            "salaam_prelaunch_readiness.group_readiness_manager"
        )
        for rec in self:
            if not rec.tracker_id:
                continue
            state = rec.tracker_id.state
            if state == "closed":
                raise UserError(_(
                    "Tracker '%s' is closed. Items cannot be modified."
                ) % rec.tracker_id.display_name)
            if state == "locked" and not (bypass and is_manager):
                raise UserError(_(
                    "Tracker '%(name)s' is locked for Decision Gate review. "
                    "Reset to Draft (manager only) to edit items."
                ) % {"name": rec.tracker_id.display_name})

    # ----- Quick-edit actions for the kanban / list ----------------------
    def action_mark_done(self):
        for rec in self:
            rec.write({"status": "done", "pct_complete": 100.0})
            rec.message_post(body=_("Marked Done."))
        return True

    def action_mark_in_progress(self):
        for rec in self:
            rec.status = "in_progress"
        return True

    def action_mark_blocked(self):
        for rec in self:
            rec.write({"status": "blocked", "pct_complete": 0.0})
            rec.message_post(
                body=_("Marked Blocked. Hard-gate progress on category "
                       "'%s' is now stalled.") % rec.category_id.display_name,
            )
            # Notify the tracker creator
            if rec.tracker_id and rec.tracker_id.create_uid:
                rec.tracker_id.activity_schedule(
                    "mail.mail_activity_data_warning",
                    summary=_("Readiness item blocked: %s") % rec.name,
                    note=_("Item '%s' (Cat %s) is blocked. Please review.")
                         % (rec.name, rec.category_code),
                    user_id=rec.tracker_id.create_uid.id,
                )
        return True

    def action_open_linked_record(self):
        self.ensure_one()
        if not self.linked_record_ref:
            raise UserError(_("No linked record set on this item."))
        ref = self.linked_record_ref
        return {
            "type": "ir.actions.act_window",
            "name": _("Linked Record"),
            "res_model": ref._name,
            "res_id": ref.id,
            "view_mode": "form",
            "target": "current",
        }
