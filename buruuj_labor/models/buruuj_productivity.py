# -*- coding: utf-8 -*-
from odoo import models, fields, api


class BuruujProductivity(models.Model):
    """Output measurement: how much work was produced per crew per day.

    Used to track crews against benchmark productivity, identify under-performing
    activities, and inform future estimating."""
    _name = "buruuj.productivity"
    _description = "Daily Productivity Record"
    _order = "date desc, project_id"

    project_id = fields.Many2one("project.project", required=True)
    phase_id = fields.Many2one("buruuj.phase",
                                 domain="[('project_id','=',project_id)]")
    cbs_id = fields.Many2one(
        "buruuj.cbs",
        domain="[('project_id','=',project_id),('is_leaf','=',True)]")
    activity = fields.Char(string="Activity / Work Item", required=True)
    date = fields.Date(required=True, default=fields.Date.context_today)

    # Crew composition
    crew_name = fields.Char(string="Crew / Foreman", required=True)
    crew_size = fields.Integer(string="Crew Size")
    foreman_id = fields.Many2one("buruuj.worker",
                                   domain=[("trade_id.skill_level", "in",
                                              ["foreman", "supervisor"])])

    # Inputs
    hours_consumed = fields.Float(string="Total Hours Consumed",
                                     help="Sum of crew hours for this activity.")

    # Outputs
    output_quantity = fields.Float(string="Output Quantity")
    output_uom = fields.Char(string="UoM",
                                help="m3, m2, kg, ton, no, lump_sum, etc.")

    # Computed
    productivity = fields.Float(string="Productivity (hrs/unit)",
                                  compute="_compute_productivity", store=True,
                                  help="Hours required to produce one unit. Lower = better.")
    inverse_productivity = fields.Float(
        string="Output Rate (units/hr)",
        compute="_compute_productivity", store=True,
        help="Units produced per hour. Higher = better.")

    benchmark_productivity = fields.Float(
        string="Benchmark (hrs/unit)",
        help="Expected productivity from estimating. Compare actual.")
    variance_pct = fields.Float(string="Variance %",
                                  compute="_compute_productivity", store=True,
                                  help="Negative means worse than benchmark.")

    notes = fields.Text()
    captured_by = fields.Many2one("res.users",
                                    default=lambda s: s.env.user)
    company_id = fields.Many2one("res.company",
                                   default=lambda s: s.env.company)

    @api.depends("hours_consumed", "output_quantity", "benchmark_productivity")
    def _compute_productivity(self):
        for rec in self:
            if rec.output_quantity:
                rec.productivity = rec.hours_consumed / rec.output_quantity
                rec.inverse_productivity = rec.output_quantity / rec.hours_consumed
                if rec.benchmark_productivity:
                    # Negative variance = took longer than benchmark
                    rec.variance_pct = ((rec.benchmark_productivity - rec.productivity)
                                          / rec.benchmark_productivity * 100.0)
                else:
                    rec.variance_pct = 0.0
            else:
                rec.productivity = 0.0
                rec.inverse_productivity = 0.0
                rec.variance_pct = 0.0
