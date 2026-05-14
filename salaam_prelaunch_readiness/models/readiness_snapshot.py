# -*- coding: utf-8 -*-
"""
Readiness Snapshot - immutable archive of tracker state at lock time.

Created automatically when a tracker is locked for Decision Gate 0
review. Cannot be edited or deleted (write/unlink raise). The line
table replicates each item's status, % complete, owner, due date,
evidence link, and notes at the moment of lock - so later edits to
the live tracker do not retroactively rewrite gate evidence.
"""
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class ReadinessSnapshot(models.Model):
    _name = "salaam.readiness.snapshot"
    _description = "Salaam Pre-Launch Readiness Snapshot (write-once)"
    _order = "snapshot_date desc, id desc"
    _rec_name = "display_name"

    display_name = fields.Char(
        string="Name",
        compute="_compute_display_name",
        store=True,
    )

    tracker_id = fields.Many2one(
        "salaam.readiness.tracker",
        string="Tracker",
        required=True,
        ondelete="restrict",
        index=True,
    )
    snapshot_date = fields.Datetime(
        string="Lock Time",
        required=True,
        default=fields.Datetime.now,
        readonly=True,
    )
    locked_by = fields.Many2one(
        "res.users",
        string="Locked By",
        required=True,
        default=lambda self: self.env.user,
        readonly=True,
    )

    # ----- Frozen aggregates ---------------------------------------------
    overall_pct = fields.Float(string="Overall %", digits=(5, 2), readonly=True)
    hard_gate_pct = fields.Float(string="Hard Gate %", digits=(5, 2), readonly=True)
    parallel_pct = fields.Float(string="Parallel %", digits=(5, 2), readonly=True)
    mob_pct = fields.Float(string="Mobilization %", digits=(5, 2), readonly=True)
    is_ready_to_mobilize = fields.Boolean(
        string="Ready to Mobilize", readonly=True,
    )
    readiness_status = fields.Selection(
        [
            ("blocked", "Blocked"),
            ("at_risk", "At Risk"),
            ("on_track", "On Track"),
            ("ready", "Ready to Mobilize"),
        ],
        string="Status",
        readonly=True,
    )
    total_items = fields.Integer(string="Total Items", readonly=True)
    blocked_count = fields.Integer(string="Blocked Items", readonly=True)

    line_ids = fields.One2many(
        "salaam.readiness.snapshot.line",
        "snapshot_id",
        string="Item Snapshots",
        readonly=True,
    )

    notes = fields.Text(
        string="Lock Notes",
        help="Optional context posted by the locking user.",
    )

    # ----- Compute -------------------------------------------------------
    @api.depends("tracker_id", "snapshot_date")
    def _compute_display_name(self):
        for rec in self:
            if rec.tracker_id and rec.snapshot_date:
                rec.display_name = "%s @ %s" % (
                    rec.tracker_id.display_name,
                    fields.Datetime.to_string(rec.snapshot_date),
                )
            else:
                rec.display_name = _("Snapshot")

    # ----- Write-once enforcement ----------------------------------------
    def write(self, vals):
        # Allow writes during create flow only (when no record exists yet,
        # write is the bulk-set after insert). After the record has lines,
        # block all writes except to 'notes' which can be appended.
        ALLOWED = {"notes"}
        for rec in self:
            disallowed = set(vals.keys()) - ALLOWED
            if disallowed:
                raise UserError(_(
                    "Snapshots are write-once. Cannot modify: %s"
                ) % ", ".join(sorted(disallowed)))
        return super().write(vals)

    def unlink(self):
        # Manager group can delete (admin recovery), but log it.
        if not self.env.user.has_group(
            "salaam_prelaunch_readiness.group_readiness_manager"
        ):
            raise UserError(_(
                "Only managers can delete a snapshot, and only for "
                "administrative correction."
            ))
        for rec in self:
            rec.tracker_id.message_post(
                body=_("Snapshot from %s deleted by %s.") % (
                    fields.Datetime.to_string(rec.snapshot_date),
                    self.env.user.display_name,
                ),
            )
        return super().unlink()

    # ----- Action: print PDF evidence pack -------------------------------
    def action_print_evidence_pack(self):
        self.ensure_one()
        return self.env.ref(
            "salaam_prelaunch_readiness.action_report_readiness_evidence_pack"
        ).report_action(self)


class ReadinessSnapshotLine(models.Model):
    _name = "salaam.readiness.snapshot.line"
    _description = "Salaam Readiness Snapshot Line (frozen item)"
    _order = "snapshot_id, category_code, sequence"

    snapshot_id = fields.Many2one(
        "salaam.readiness.snapshot",
        string="Snapshot",
        required=True,
        ondelete="cascade",
        index=True,
    )
    # Frozen copies of the item fields - no relations to the live item
    # so deletion of a live item does not orphan the snapshot.
    category_code = fields.Char(string="Cat", readonly=True)
    category_name = fields.Char(string="Category", readonly=True)
    gate_type = fields.Selection(
        [("hard", "Hard"), ("parallel", "Parallel"), ("mob", "Mobilization")],
        string="Gate", readonly=True,
    )
    sequence = fields.Integer(string="#", readonly=True)
    name = fields.Char(string="Item", readonly=True)
    status = fields.Selection(
        [
            ("not_started", "Not Started"),
            ("in_progress", "In Progress"),
            ("done", "Done"),
            ("blocked", "Blocked"),
            ("na", "N/A"),
        ],
        string="Status",
        readonly=True,
    )
    pct_complete = fields.Float(string="%", digits=(5, 2), readonly=True)
    owner_login = fields.Char(string="Owner", readonly=True)
    due_date = fields.Date(string="Due", readonly=True)
    evidence_url = fields.Char(string="Evidence", readonly=True)
    notes = fields.Text(string="Notes", readonly=True)

    # Block all writes to the line - the snapshot is frozen
    def write(self, vals):
        raise UserError(_("Snapshot lines are immutable."))

    def unlink(self):
        # Lines unlink only via cascade when the parent snapshot is deleted
        # by a manager. Block direct unlink.
        if self.env.context.get("salaam_snapshot_cascade_unlink"):
            return super().unlink()
        raise UserError(_(
            "Snapshot lines cannot be deleted individually."
        ))
