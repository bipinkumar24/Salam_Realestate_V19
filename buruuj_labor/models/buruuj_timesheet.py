# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class BuruujTimesheet(models.Model):
    """Worker's hours booked against project / phase / activity.

    Aggregates roll up into wage runs and into productivity calculations."""
    _name = "buruuj.timesheet"
    _description = "Labor Timesheet"
    _order = "date desc, worker_id"

    worker_id = fields.Many2one("buruuj.worker", required=True,
                                  ondelete="cascade")
    trade_id = fields.Many2one(related="worker_id.trade_id", store=True)
    employment_type = fields.Selection(related="worker_id.employment_type",
                                          store=True)
    daily_rate = fields.Monetary(related="worker_id.daily_rate", store=True)
    hourly_rate = fields.Monetary(related="worker_id.hourly_rate", store=True)

    project_id = fields.Many2one("project.project", required=True)
    phase_id = fields.Many2one("buruuj.phase",
                                 domain="[('project_id','=',project_id)]")
    cbs_id = fields.Many2one(
        "buruuj.cbs", string="Cost Breakdown Line",
        domain="[('project_id','=',project_id),('is_leaf','=',True)]")
    subcontract_id = fields.Many2one(
        "buruuj.subcontract",
        domain="[('project_id','=',project_id)]")
    workorder_id = fields.Many2one("buruuj.workorder")
    boq_line_id = fields.Many2one(
        "buruuj.boq.line", string="BOQ Item",
        domain="[('boq_id.project_id', '=', project_id)]",
        help="BOQ item these labor hours are booked against. "
             "Used to compare actual vs estimated labor cost per BOQ line.")
    activity = fields.Char(string="Activity")

    date = fields.Date(required=True, default=fields.Date.context_today,
                         index=True)
    regular_hours = fields.Float(default=0.0)
    overtime_hours = fields.Float(default=0.0)
    total_hours = fields.Float(compute="_compute_totals", store=True)

    regular_cost = fields.Monetary(compute="_compute_totals", store=True)
    overtime_cost = fields.Monetary(compute="_compute_totals", store=True)
    total_cost = fields.Monetary(compute="_compute_totals", store=True)

    wage_run_id = fields.Many2one("buruuj.wage.run", readonly=True,
                                    copy=False)
    state = fields.Selection([
        ("draft", "Draft"),
        ("submitted", "Submitted"),
        ("approved", "Approved"),
        ("paid", "In Wage Run"),
    ], default="draft")

    captured_by = fields.Many2one("res.users",
                                    default=lambda s: s.env.user)
    notes = fields.Char()

    currency_id = fields.Many2one(
        "res.currency", default=lambda s: s.env.company.currency_id)
    company_id = fields.Many2one("res.company",
                                   default=lambda s: s.env.company)

    @api.depends("regular_hours", "overtime_hours", "hourly_rate", "daily_rate",
                 "worker_id.overtime_rate_multiplier")
    def _compute_totals(self):
        for rec in self:
            rec.total_hours = rec.regular_hours + rec.overtime_hours
            # If hourly rate set, use that; otherwise derive from daily rate / 8
            base_hourly = rec.hourly_rate or (rec.daily_rate / 8.0 if rec.daily_rate else 0.0)
            ot_mult = rec.worker_id.overtime_rate_multiplier or 1.5
            rec.regular_cost = rec.regular_hours * base_hourly
            rec.overtime_cost = rec.overtime_hours * base_hourly * ot_mult
            rec.total_cost = rec.regular_cost + rec.overtime_cost

    def action_submit(self):
        self.write({"state": "submitted"})

    def action_approve(self):
        self.write({"state": "approved"})

    def action_back_to_draft(self):
        for rec in self:
            if rec.wage_run_id:
                raise UserError(_(
                    "Cannot revert — already included in wage run %s.") % rec.wage_run_id.name)
            rec.state = "draft"
