# -*- coding: utf-8 -*-
"""
Pre-Launch Readiness Category - the 14 buckets (A-N).

Each category has a fixed gate type (hard / parallel / mob) and a
computed completion %. The traffic-light status_color drives kanban
and dashboard rendering.
"""
from odoo import api, fields, models, _


GATE_TYPE_REQUIRED = {
    "hard": 100.0,
    "parallel": 80.0,
    "mob": 100.0,
}


class ReadinessCategory(models.Model):
    _name = "salaam.readiness.category"
    _description = "Salaam Pre-Launch Readiness Category"
    _order = "tracker_id, sequence, code"
    _rec_name = "display_name"

    tracker_id = fields.Many2one(
        "salaam.readiness.tracker",
        string="Tracker",
        required=True,
        ondelete="cascade",
        index=True,
    )
    code = fields.Char(string="Code", required=True, size=2)
    name = fields.Char(string="Category", required=True, translate=True)
    display_name = fields.Char(
        string="Display Name",
        compute="_compute_display_name",
        store=True,
    )
    sequence = fields.Integer(string="Sequence", default=10)

    gate_type = fields.Selection(
        [
            ("hard", "Hard Gate"),
            ("parallel", "Parallel"),
            ("mob", "Mobilization"),
        ],
        string="Gate Type",
        required=True,
        default="parallel",
    )
    required_pct = fields.Float(
        string="Required %",
        compute="_compute_required_pct",
        store=True,
    )

    item_ids = fields.One2many(
        "salaam.readiness.item",
        "category_id",
        string="Items",
    )

    # ---- Aggregates ------------------------------------------------------
    total_count = fields.Integer(
        string="Total Items",
        compute="_compute_counts",
        store=True,
    )
    done_count = fields.Integer(
        string="Done",
        compute="_compute_counts",
        store=True,
    )
    in_progress_count = fields.Integer(
        string="In Progress",
        compute="_compute_counts",
        store=True,
    )
    blocked_count = fields.Integer(
        string="Blocked",
        compute="_compute_counts",
        store=True,
    )
    not_started_count = fields.Integer(
        string="Not Started",
        compute="_compute_counts",
        store=True,
    )
    na_count = fields.Integer(
        string="N/A",
        compute="_compute_counts",
        store=True,
    )
    overdue_count = fields.Integer(
        string="Overdue",
        compute="_compute_counts",
        store=True,
    )
    pct_complete = fields.Float(
        string="% Complete",
        compute="_compute_counts",
        store=True,
        digits=(5, 2),
    )
    status_color = fields.Selection(
        [
            ("green", "Green - On Target"),
            ("amber", "Amber - At Risk"),
            ("red", "Red - Blocked / Behind"),
        ],
        string="Status",
        compute="_compute_counts",
        store=True,
    )

    # ----- Compute --------------------------------------------------------
    @api.depends("code", "name")
    def _compute_display_name(self):
        for rec in self:
            rec.display_name = (
                f"{rec.code}. {rec.name}" if rec.code and rec.name else (rec.name or "")
            )

    @api.depends("gate_type")
    def _compute_required_pct(self):
        for rec in self:
            rec.required_pct = GATE_TYPE_REQUIRED.get(rec.gate_type, 80.0)

    @api.depends(
        "item_ids",
        "item_ids.status",
        "item_ids.pct_complete",
        "item_ids.is_overdue",
    )
    def _compute_counts(self):
        for rec in self:
            items = rec.item_ids
            # N/A items are excluded from the denominator
            counted = items.filtered(lambda i: i.status != "na")
            total = len(counted)
            done = len(items.filtered(lambda i: i.status == "done"))
            in_prog = len(items.filtered(lambda i: i.status == "in_progress"))
            blocked = len(items.filtered(lambda i: i.status == "blocked"))
            not_started = len(items.filtered(lambda i: i.status == "not_started"))
            na = len(items.filtered(lambda i: i.status == "na"))
            overdue = len(items.filtered(lambda i: i.is_overdue))

            rec.total_count = total
            rec.done_count = done
            rec.in_progress_count = in_prog
            rec.blocked_count = blocked
            rec.not_started_count = not_started
            rec.na_count = na
            rec.overdue_count = overdue

            if total:
                rec.pct_complete = sum(i.pct_complete for i in counted) / total
            else:
                rec.pct_complete = 0.0

            # Traffic light
            if blocked:
                rec.status_color = "red"
            elif rec.pct_complete >= rec.required_pct:
                rec.status_color = "green"
            elif rec.pct_complete >= max(rec.required_pct - 20.0, 50.0):
                rec.status_color = "amber"
            else:
                rec.status_color = "red"

    # ----- Actions --------------------------------------------------------
    def action_open_items(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("%s - Items") % self.display_name,
            "res_model": "salaam.readiness.item",
            "view_mode": "list,form,kanban",
            "domain": [("category_id", "=", self.id)],
            "context": {"default_category_id": self.id},
        }
