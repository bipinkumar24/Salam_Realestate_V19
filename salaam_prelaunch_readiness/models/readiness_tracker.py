# -*- coding: utf-8 -*-
"""
Pre-Launch Readiness Tracker - header record.

One tracker per (Phase, Lot) combination. Aggregates the 14 categories
and computes the Go / No-Go signal for the Decision Gate 0 record in
``salaam_execution_plan``.
"""
from odoo import api, fields, models, _
from odoo.exceptions import UserError


HARD_GATE_CODES = ("A", "B", "C", "D", "F", "G", "M")
PARALLEL_CODES = ("E", "H", "I", "J", "K", "L")
MOB_CODES = ("N",)

PARALLEL_THRESHOLD = 80.0  # %


class ReadinessTracker(models.Model):
    _name = "salaam.readiness.tracker"
    _description = "Salaam Pre-Launch Readiness Tracker"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "create_date desc, id desc"

    name = fields.Char(
        string="Name",
        required=True,
        tracking=True,
        default="Pre-Launch Readiness Tracker",
    )

    # Phase / Lot identifiers - kept as labels (Char) to avoid hard
    # dependencies on a specific model name in salaam_execution_plan;
    # tighten to M2O fields in v1.1 once the production model name is
    # confirmed for this tenant.
    phase_label = fields.Char(string="Phase", tracking=True)
    lot_label = fields.Char(string="Lot", tracking=True)

    # Reference to the linked Decision Gate 0 record. Reference field
    # so this works against whatever model salaam_execution_plan uses
    # without forcing a hard schema link.
    decision_gate_ref = fields.Reference(
        selection="_selection_decision_gate_models",
        string="Decision Gate 0",
        help="The Decision Gate 0 record in salaam_execution_plan that "
             "this tracker provides evidence for.",
    )

    company_id = fields.Many2one(
        "res.company",
        string="Company",
        default=lambda self: self.env.company,
        required=True,
    )
    currency_id = fields.Many2one(
        "res.currency",
        related="company_id.currency_id",
        store=True,
        readonly=True,
    )

    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("active", "Active"),
            ("locked", "Locked for Gate Review"),
            ("closed", "Closed"),
        ],
        string="Status",
        default="draft",
        required=True,
        tracking=True,
        copy=False,
    )

    category_ids = fields.One2many(
        "salaam.readiness.category",
        "tracker_id",
        string="Categories",
    )
    item_ids = fields.One2many(
        "salaam.readiness.item",
        "tracker_id",
        string="All Items",
    )
    snapshot_ids = fields.One2many(
        "salaam.readiness.snapshot",
        "tracker_id",
        string="Lock Snapshots",
        help="Immutable archive of the tracker state at each lock-for-"
             "gate-review event. Decision Gate 0 evidence trail.",
    )
    snapshot_count = fields.Integer(
        string="Snapshots",
        compute="_compute_snapshot_count",
    )

    # ----- Aggregate counts -----------------------------------------------
    total_items = fields.Integer(
        string="Total Items",
        compute="_compute_aggregate",
        store=True,
    )
    done_count = fields.Integer(
        string="Done",
        compute="_compute_aggregate",
        store=True,
    )
    in_progress_count = fields.Integer(
        string="In Progress",
        compute="_compute_aggregate",
        store=True,
    )
    blocked_count = fields.Integer(
        string="Blocked",
        compute="_compute_aggregate",
        store=True,
    )
    overdue_count = fields.Integer(
        string="Overdue",
        compute="_compute_aggregate",
        store=True,
    )

    # ----- Aggregate percentages ------------------------------------------
    overall_pct = fields.Float(
        string="Overall % Complete",
        compute="_compute_aggregate",
        store=True,
        digits=(5, 2),
    )
    hard_gate_pct = fields.Float(
        string="Hard Gate %",
        compute="_compute_aggregate",
        store=True,
        digits=(5, 2),
    )
    parallel_pct = fields.Float(
        string="Parallel %",
        compute="_compute_aggregate",
        store=True,
        digits=(5, 2),
    )
    mob_pct = fields.Float(
        string="Mobilization %",
        compute="_compute_aggregate",
        store=True,
        digits=(5, 2),
    )

    # ----- Go / No-Go signal ----------------------------------------------
    is_ready_to_mobilize = fields.Boolean(
        string="Ready to Mobilize",
        compute="_compute_aggregate",
        store=True,
        help="True when all hard gates are 100%, all parallel categories "
             "are at or above 80%, and mobilization is 100%.",
    )
    readiness_status = fields.Selection(
        [
            ("blocked", "Blocked"),
            ("at_risk", "At Risk"),
            ("on_track", "On Track"),
            ("ready", "Ready to Mobilize"),
        ],
        string="Readiness Status",
        compute="_compute_aggregate",
        store=True,
    )

    # ----- Selection helper for Reference field ---------------------------
    @api.model
    def _selection_decision_gate_models(self):
        """Whitelist of models that may be referenced as Decision Gate 0.

        Kept narrow so users don't accidentally point this at unrelated
        records. Add models here as the tenant identifies the canonical
        gate model in salaam_execution_plan.
        """
        candidates = [
            ("salaam.decision.gate", "Decision Gate"),
            ("salaam.execution.decision.gate", "Execution Plan: Decision Gate"),
            ("salaam.execution.plan.gate", "Execution Plan: Gate"),
        ]
        # Filter to the models that actually exist in this database
        existing = []
        for model_name, label in candidates:
            if model_name in self.env:
                existing.append((model_name, label))
        return existing or [("salaam.readiness.tracker", "(no gate model installed)")]

    # ----- Compute --------------------------------------------------------
    @api.depends(
        "category_ids",
        "category_ids.gate_type",
        "category_ids.pct_complete",
        "category_ids.total_count",
        "category_ids.done_count",
        "category_ids.blocked_count",
        "category_ids.in_progress_count",
        "category_ids.overdue_count",
    )
    def _compute_aggregate(self):
        for rec in self:
            cats = rec.category_ids
            total = sum(c.total_count for c in cats)
            done = sum(c.done_count for c in cats)
            in_prog = sum(c.in_progress_count for c in cats)
            blocked = sum(c.blocked_count for c in cats)
            overdue = sum(c.overdue_count for c in cats)

            rec.total_items = total
            rec.done_count = done
            rec.in_progress_count = in_prog
            rec.blocked_count = blocked
            rec.overdue_count = overdue
            rec.overall_pct = (
                sum(c.pct_complete * c.total_count for c in cats) / total
                if total else 0.0
            )

            hard = cats.filtered(lambda c: c.code in HARD_GATE_CODES)
            par = cats.filtered(lambda c: c.code in PARALLEL_CODES)
            mob = cats.filtered(lambda c: c.code in MOB_CODES)

            rec.hard_gate_pct = (
                sum(c.pct_complete * c.total_count for c in hard) /
                sum(c.total_count for c in hard)
                if sum(c.total_count for c in hard) else 0.0
            )
            rec.parallel_pct = (
                sum(c.pct_complete * c.total_count for c in par) /
                sum(c.total_count for c in par)
                if sum(c.total_count for c in par) else 0.0
            )
            rec.mob_pct = (
                sum(c.pct_complete * c.total_count for c in mob) /
                sum(c.total_count for c in mob)
                if sum(c.total_count for c in mob) else 0.0
            )

            # Ready-to-mobilize gate logic:
            # every hard category at 100, every parallel >= 80, every mob at 100,
            # AND zero blocked items.
            ready = bool(cats) and blocked == 0
            for c in hard:
                if c.pct_complete < 100.0:
                    ready = False
                    break
            if ready:
                for c in par:
                    if c.pct_complete < PARALLEL_THRESHOLD:
                        ready = False
                        break
            if ready:
                for c in mob:
                    if c.pct_complete < 100.0:
                        ready = False
                        break
            rec.is_ready_to_mobilize = ready

            # Traffic light:
            #   blocked    - any blocked item
            #   ready      - gate logic satisfied
            #   on_track   - hard gate >= 70 and no blocked
            #   at_risk    - everything else
            if blocked:
                rec.readiness_status = "blocked"
            elif ready:
                rec.readiness_status = "ready"
            elif rec.hard_gate_pct >= 70.0:
                rec.readiness_status = "on_track"
            else:
                rec.readiness_status = "at_risk"

    # ----- Workflow buttons -----------------------------------------------
    def action_activate(self):
        for rec in self:
            if rec.state != "draft":
                raise UserError(_("Only draft trackers can be activated."))
            rec.state = "active"
            rec.message_post(body=_("Tracker activated. Items are now editable."))
        return True

    def action_lock_for_gate_review(self):
        for rec in self:
            if rec.state != "active":
                raise UserError(_("Only active trackers can be locked."))
            rec.state = "locked"

            # Create the immutable snapshot - this is the Decision Gate 0
            # evidence record. Even if the tracker is later unlocked and
            # edited, this snapshot stays put.
            snapshot = self.env["salaam.readiness.snapshot"].create({
                "tracker_id": rec.id,
                "overall_pct": rec.overall_pct,
                "hard_gate_pct": rec.hard_gate_pct,
                "parallel_pct": rec.parallel_pct,
                "mob_pct": rec.mob_pct,
                "is_ready_to_mobilize": rec.is_ready_to_mobilize,
                "readiness_status": rec.readiness_status,
                "total_items": rec.total_items,
                "blocked_count": rec.blocked_count,
            })
            line_vals = []
            for it in rec.item_ids:
                line_vals.append({
                    "snapshot_id": snapshot.id,
                    "category_code": it.category_code,
                    "category_name": it.category_id.name,
                    "gate_type": it.gate_type,
                    "sequence": it.sequence,
                    "name": it.name,
                    "status": it.status,
                    "pct_complete": it.pct_complete,
                    "owner_login": it.owner_id.login if it.owner_id else False,
                    "due_date": it.due_date,
                    "evidence_url": it.evidence_url,
                    "notes": it.notes,
                })
            self.env["salaam.readiness.snapshot.line"].create(line_vals)

            rec.message_post(
                body=_("Tracker locked for Decision Gate 0 review. "
                       "Snapshot #%(sid)d archived. "
                       "Overall: %(pct).1f%%  -  Hard: %(h).1f%%  -  "
                       "Parallel: %(p).1f%%  -  Mob: %(m).1f%%") % {
                    "sid": snapshot.id,
                    "pct": rec.overall_pct,
                    "h": rec.hard_gate_pct,
                    "p": rec.parallel_pct,
                    "m": rec.mob_pct,
                },
            )
            if rec.is_ready_to_mobilize and rec.decision_gate_ref:
                # Post evidence note on the gate record
                gate = rec.decision_gate_ref
                if hasattr(gate, "message_post"):
                    gate.message_post(
                        body=_("Pre-Launch Readiness reports READY TO MOBILIZE. "
                               "Evidence: %s") % rec.display_name,
                    )
        return True

    def action_close(self):
        for rec in self:
            rec.state = "closed"
            rec.message_post(body=_("Tracker closed."))
        return True

    def action_reset_to_draft(self):
        for rec in self:
            if rec.state == "closed":
                raise UserError(_("Closed trackers cannot be reopened."))
            rec.state = "draft"
            rec.message_post(
                body=_("Tracker reset to Draft. Lock snapshots remain immutable; "
                       "the next Lock will create a new snapshot."),
            )
        return True

    @api.depends("snapshot_ids")
    def _compute_snapshot_count(self):
        for rec in self:
            rec.snapshot_count = len(rec.snapshot_ids)

    def action_open_snapshots(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("%s - Snapshots") % self.name,
            "res_model": "salaam.readiness.snapshot",
            "view_mode": "list,form",
            "domain": [("tracker_id", "=", self.id)],
            "context": {"default_tracker_id": self.id},
        }

    def action_open_clone_wizard(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Clone Tracker"),
            "res_model": "salaam.readiness.clone.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {"default_source_tracker_id": self.id},
        }

    # ----- Cron -----------------------------------------------------------
    @api.model
    def _cron_recompute_readiness(self):
        """Nightly recompute. Triggered by ir.cron.

        Forces dependency recomputation on every active tracker so the
        IAFAO dashboard sees fresh KPIs even if no item changed today.
        Also raises hard-gate-blocked alerts.
        """
        active = self.search([("state", "in", ("active", "locked"))])
        active.invalidate_recordset(
            ["overall_pct", "hard_gate_pct", "parallel_pct", "mob_pct",
             "is_ready_to_mobilize", "readiness_status"]
        )
        # Touching a stored compute field forces re-eval
        active._compute_aggregate()

        for rec in active:
            if rec.blocked_count and rec.state == "active":
                rec.activity_schedule(
                    "mail.mail_activity_data_warning",
                    summary=_("Blocked readiness items - urgent"),
                    note=_("%d item(s) on this tracker are blocked. "
                           "Hard-gate progress is stalled.") % rec.blocked_count,
                    user_id=(rec.create_uid or self.env.user).id,
                )
        return True

    # ----- Action: open all items ----------------------------------------
    def action_open_items(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("%s - Items") % self.name,
            "res_model": "salaam.readiness.item",
            "view_mode": "list,form,kanban,pivot",
            "domain": [("tracker_id", "=", self.id)],
            "context": {"default_tracker_id": self.id, "search_default_group_category": 1},
        }

    def action_open_excel_import(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Import Status from Excel"),
            "res_model": "salaam.readiness.excel.import",
            "view_mode": "form",
            "target": "new",
            "context": {"default_tracker_id": self.id},
        }
