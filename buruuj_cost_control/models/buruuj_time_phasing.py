# -*- coding: utf-8 -*-
from odoo import models, fields, api


class BuruujTimePhasing(models.Model):
    """Time-phased budget: planned spend per month per CBS line.

    Used to compute BCWS for earned value, and to draw the S-curve."""
    _name = "buruuj.time.phasing"
    _description = "Time-Phased Budget"
    _order = "project_id, date, id"

    project_id = fields.Many2one("project.project", required=True,
                                   ondelete="cascade")
    cbs_id = fields.Many2one("buruuj.cbs",
                               domain="[('project_id','=',project_id)]",
                               help="Optional. Leave blank for project-level phasing.")
    date = fields.Date(string="Period (Month End)", required=True,
                         help="The last day of the month this phasing applies to.")
    period_label = fields.Char(compute="_compute_period_label", store=True)
    planned_amount = fields.Monetary(string="Planned Spend")
    cumulative_planned = fields.Monetary(string="Cumulative Planned",
                                           compute="_compute_cumulative",
                                           store=False)
    cumulative_actual = fields.Monetary(string="Cumulative Actual",
                                            compute="_compute_cumulative",
                                            store=False)

    currency_id = fields.Many2one(
        "res.currency",
        default=lambda s: s.env.company.currency_id, store=True)
    company_id = fields.Many2one("res.company",
                                   default=lambda s: s.env.company)

    @api.depends("date")
    def _compute_period_label(self):
        for rec in self:
            if rec.date:
                rec.period_label = rec.date.strftime("%b %Y")
            else:
                rec.period_label = ""

    @api.depends("project_id", "date", "planned_amount")
    def _compute_cumulative(self):
        # For each row, cumulative is sum of planned and actual up to its date.
        # Group by project for efficiency.
        by_project = {}
        for rec in self:
            by_project.setdefault(rec.project_id.id, []).append(rec)
        for proj_id, recs in by_project.items():
            recs_sorted = sorted(recs, key=lambda r: r.date or fields.Date.today())
            running = 0.0
            for r in recs_sorted:
                running += r.planned_amount
                r.cumulative_planned = running
                # Actual from cost entries up to this date
                actual = sum(self.env["buruuj.cost.entry"].search([
                    ("project_id", "=", proj_id),
                    ("entry_type", "=", "actual"),
                    ("date", "<=", r.date),
                ]).mapped("amount"))
                r.cumulative_actual = actual
