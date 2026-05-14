# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class BuruujCBS(models.Model):
    """Cost Breakdown Structure line - one node in a project's cost tree.

    A CBS line holds: budget (frozen baseline), committed (signed but not paid),
    actual (paid/billed), and forecast at completion.

    Lines can be hierarchical (parent/child) for rollup reporting."""
    _name = "buruuj.cbs"
    _description = "Cost Breakdown Structure Line"
    _inherit = ["mail.thread"]
    _parent_store = True
    _order = "project_id, sequence, code"

    name = fields.Char(required=True, tracking=True)
    code = fields.Char(string="CBS Code", required=True, copy=False, tracking=True,
                         help="Hierarchical code, e.g., 1.0, 1.1, 1.1.1")
    sequence = fields.Integer(default=10)

    project_id = fields.Many2one("project.project", required=True,
                                   ondelete="cascade", tracking=True)
    parent_id = fields.Many2one("buruuj.cbs", string="Parent",
                                  ondelete="cascade",
                                  domain="[('project_id','=',project_id)]")
    parent_path = fields.Char(index=True)
    child_ids = fields.One2many("buruuj.cbs", "parent_id", string="Children")
    is_leaf = fields.Boolean(compute="_compute_is_leaf", store=True)

    category_id = fields.Many2one("buruuj.cost.category", required=True,
                                    tracking=True)
    cost_type = fields.Selection(related="category_id.cost_type", store=True)
    phase_id = fields.Many2one("buruuj.phase",
                                 domain="[('project_id','=',project_id)]")

    # Budget — set once, frozen unless explicitly revised
    baseline_budget = fields.Monetary(string="Baseline Budget", tracking=True)
    revised_budget = fields.Monetary(string="Revised Budget", tracking=True,
                                       help="Baseline + approved variations / transfers.")
    budget_locked = fields.Boolean(default=False, tracking=True,
                                     help="When set, baseline cannot be modified.")

    # Computed totals from cost entries (committed and actual)
    committed_amount = fields.Monetary(compute="_compute_amounts", store=True)
    actual_amount = fields.Monetary(compute="_compute_amounts", store=True)
    estimate_to_complete = fields.Monetary(string="Estimate to Complete (ETC)",
                                              tracking=True,
                                              help="Cost officer's forecast of remaining costs to finish this CBS line.")
    forecast_at_completion = fields.Monetary(
        string="Forecast at Completion (FAC)",
        compute="_compute_amounts", store=True)
    variance_at_completion = fields.Monetary(
        string="Variance at Completion (VAC)",
        compute="_compute_amounts", store=True,
        help="Revised Budget - FAC. Negative means overrun.")
    variance_pct = fields.Float(string="Variance %",
                                  compute="_compute_amounts", store=True)

    # Rollups (when this line has children)
    rollup_baseline = fields.Monetary(compute="_compute_rollups", store=True)
    rollup_revised = fields.Monetary(compute="_compute_rollups", store=True)
    rollup_committed = fields.Monetary(compute="_compute_rollups", store=True)
    rollup_actual = fields.Monetary(compute="_compute_rollups", store=True)
    rollup_etc = fields.Monetary(compute="_compute_rollups", store=True)
    rollup_fac = fields.Monetary(compute="_compute_rollups", store=True)
    rollup_vac = fields.Monetary(compute="_compute_rollups", store=True)

    # % complete (physical) — drives earned value
    physical_progress = fields.Float(
        string="Physical Progress %",
        help="Manual progress estimate. Drives BCWP (earned value).")

    cost_entry_ids = fields.One2many("buruuj.cost.entry", "cbs_id")
    cost_entry_count = fields.Integer(compute="_compute_entry_count")

    notes = fields.Text()
    active = fields.Boolean(default=True)
    currency_id = fields.Many2one(
        "res.currency",
        default=lambda s: s.env.company.currency_id, store=True)
    company_id = fields.Many2one("res.company",
                                   default=lambda s: s.env.company)

    _sql_constraints = [
        ("code_project_unique", "unique(code, project_id, company_id)",
         "CBS code must be unique within a project."),
    ]

    @api.depends("child_ids")
    def _compute_is_leaf(self):
        for rec in self:
            rec.is_leaf = not rec.child_ids

    @api.depends("cost_entry_ids.amount", "cost_entry_ids.entry_type",
                 "estimate_to_complete", "revised_budget")
    def _compute_amounts(self):
        for rec in self:
            committed = sum(rec.cost_entry_ids.filtered(
                lambda e: e.entry_type == "committed").mapped("amount"))
            actual = sum(rec.cost_entry_ids.filtered(
                lambda e: e.entry_type == "actual").mapped("amount"))
            rec.committed_amount = committed
            rec.actual_amount = actual
            # FAC = Actual + outstanding commitments + ETC
            outstanding = max(0.0, committed - actual)
            rec.forecast_at_completion = actual + outstanding + rec.estimate_to_complete
            rec.variance_at_completion = rec.revised_budget - rec.forecast_at_completion
            if rec.revised_budget:
                rec.variance_pct = (rec.variance_at_completion / rec.revised_budget) * 100.0
            else:
                rec.variance_pct = 0.0

    @api.depends("child_ids.rollup_baseline", "child_ids.rollup_revised",
                 "child_ids.rollup_committed", "child_ids.rollup_actual",
                 "child_ids.rollup_etc", "child_ids.rollup_fac",
                 "baseline_budget", "revised_budget", "committed_amount",
                 "actual_amount", "estimate_to_complete",
                 "forecast_at_completion", "is_leaf")
    def _compute_rollups(self):
        for rec in self:
            if rec.is_leaf:
                rec.rollup_baseline = rec.baseline_budget
                rec.rollup_revised = rec.revised_budget
                rec.rollup_committed = rec.committed_amount
                rec.rollup_actual = rec.actual_amount
                rec.rollup_etc = rec.estimate_to_complete
                rec.rollup_fac = rec.forecast_at_completion
            else:
                rec.rollup_baseline = sum(rec.child_ids.mapped("rollup_baseline"))
                rec.rollup_revised = sum(rec.child_ids.mapped("rollup_revised"))
                rec.rollup_committed = sum(rec.child_ids.mapped("rollup_committed"))
                rec.rollup_actual = sum(rec.child_ids.mapped("rollup_actual"))
                rec.rollup_etc = sum(rec.child_ids.mapped("rollup_etc"))
                rec.rollup_fac = sum(rec.child_ids.mapped("rollup_fac"))
            rec.rollup_vac = rec.rollup_revised - rec.rollup_fac

    @api.depends("cost_entry_ids")
    def _compute_entry_count(self):
        for rec in self:
            rec.cost_entry_count = len(rec.cost_entry_ids)

    @api.constrains("parent_id", "project_id")
    def _check_parent_same_project(self):
        for rec in self:
            if rec.parent_id and rec.parent_id.project_id != rec.project_id:
                raise UserError(_(
                    "Parent CBS line must belong to the same project."))

    def write(self, vals):
        # Block baseline edit when locked, unless user is in cost officer group
        if "baseline_budget" in vals:
            for rec in self:
                if rec.budget_locked and not self.env.user.has_group(
                        "buruuj_cost_control.group_buruuj_cost_officer"):
                    raise UserError(_(
                        "Baseline budget is locked. Only the Cost Officer can modify it."))
        return super().write(vals)

    def action_lock_budget(self):
        """Lock the baseline so it can no longer be edited freely."""
        for rec in self:
            if not rec.baseline_budget:
                raise UserError(_(
                    "Cannot lock a baseline of zero. Set the budget first."))
            rec.budget_locked = True
            if not rec.revised_budget:
                rec.revised_budget = rec.baseline_budget

    def action_view_entries(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Cost Entries"),
            "res_model": "buruuj.cost.entry",
            "view_mode": "list,form",
            "domain": [("cbs_id", "=", self.id)],
            "context": {"default_cbs_id": self.id,
                          "default_project_id": self.project_id.id},
        }
