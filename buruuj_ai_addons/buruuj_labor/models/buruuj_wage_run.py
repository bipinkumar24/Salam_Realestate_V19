# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class BuruujWageRun(models.Model):
    """Periodic wage calculation. Aggregates timesheets, applies allowances
    and deductions, generates wage lines per worker, posts cost entries to
    the cost ledger."""
    _name = "buruuj.wage.run"
    _description = "Wage Run"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "period_end desc, id desc"

    name = fields.Char(copy=False, default=lambda s: _("New"), tracking=True)
    project_id = fields.Many2one("project.project", required=True,
                                   tracking=True,
                                   help="Wage run is per project — keeps cost allocation clean.")
    period_start = fields.Date(required=True, tracking=True)
    period_end = fields.Date(required=True, tracking=True)
    period_label = fields.Char(compute="_compute_period_label", store=True)

    line_ids = fields.One2many("buruuj.wage.run.line", "wage_run_id",
                                  string="Wage Lines")
    line_count = fields.Integer(compute="_compute_counts")

    # Totals
    gross_wages = fields.Monetary(compute="_compute_totals", store=True)
    total_allowances = fields.Monetary(compute="_compute_totals", store=True)
    total_deductions = fields.Monetary(compute="_compute_totals", store=True)
    net_wages = fields.Monetary(compute="_compute_totals", store=True)

    state = fields.Selection([
        ("draft", "Draft"),
        ("calculated", "Calculated"),
        ("approved", "Approved"),
        ("paid", "Paid"),
        ("cancelled", "Cancelled"),
    ], default="draft", tracking=True)

    cost_entry_id = fields.Many2one("buruuj.cost.entry", readonly=True,
                                       copy=False)

    notes = fields.Html()
    currency_id = fields.Many2one(
        "res.currency", default=lambda s: s.env.company.currency_id)
    company_id = fields.Many2one("res.company",
                                   default=lambda s: s.env.company)

    @api.depends("period_start", "period_end")
    def _compute_period_label(self):
        for rec in self:
            if rec.period_start and rec.period_end:
                rec.period_label = (f"{rec.period_start.strftime('%d %b')} - "
                                       f"{rec.period_end.strftime('%d %b %Y')}")
            else:
                rec.period_label = ""

    @api.depends("line_ids.gross", "line_ids.total_allowances",
                 "line_ids.total_deductions", "line_ids.net")
    def _compute_totals(self):
        for rec in self:
            rec.gross_wages = sum(rec.line_ids.mapped("gross"))
            rec.total_allowances = sum(rec.line_ids.mapped("total_allowances"))
            rec.total_deductions = sum(rec.line_ids.mapped("total_deductions"))
            rec.net_wages = sum(rec.line_ids.mapped("net"))

    @api.depends("line_ids")
    def _compute_counts(self):
        for rec in self:
            rec.line_count = len(rec.line_ids)

    @api.constrains("period_start", "period_end")
    def _check_dates(self):
        for rec in self:
            if rec.period_end and rec.period_start and rec.period_end < rec.period_start:
                raise UserError(_(
                    "Period end must be on or after period start."))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", _("New")) == _("New"):
                vals["name"] = self.env["ir.sequence"].next_by_code(
                    "buruuj.wage.run") or _("New")
        return super().create(vals_list)

    def action_calculate(self):
        """Pull approved timesheets in the period for this project, aggregate
        per worker, create wage lines."""
        for rec in self:
            if rec.state not in ("draft",):
                raise UserError(_("Can only calculate from Draft state."))
            # Find approved timesheets in the period for this project, not yet
            # included in another wage run
            timesheets = self.env["buruuj.timesheet"].search([
                ("project_id", "=", rec.project_id.id),
                ("date", ">=", rec.period_start),
                ("date", "<=", rec.period_end),
                ("state", "=", "approved"),
                ("wage_run_id", "=", False),
            ])
            if not timesheets:
                raise UserError(_(
                    "No approved timesheets found for this project in the period. "
                    "Approve timesheets before calculating the wage run."))
            # Group by worker
            rec.line_ids.unlink()
            workers = timesheets.mapped("worker_id")
            for worker in workers:
                worker_ts = timesheets.filtered(lambda t: t.worker_id == worker)
                line_vals = {
                    "wage_run_id": rec.id,
                    "worker_id": worker.id,
                    "regular_hours": sum(worker_ts.mapped("regular_hours")),
                    "overtime_hours": sum(worker_ts.mapped("overtime_hours")),
                    "regular_cost": sum(worker_ts.mapped("regular_cost")),
                    "overtime_cost": sum(worker_ts.mapped("overtime_cost")),
                }
                line = self.env["buruuj.wage.run.line"].create(line_vals)
                # Mark timesheets as in this wage run
                worker_ts.write({"wage_run_id": rec.id, "state": "paid"})
            rec.state = "calculated"

    def action_approve(self):
        for rec in self:
            if rec.state != "calculated":
                raise UserError(_(
                    "Wage run must be Calculated before approval."))
            rec.state = "approved"

    def action_mark_paid(self):
        """Move to paid and post a cost entry to the cost ledger."""
        for rec in self:
            if rec.state != "approved":
                raise UserError(_(
                    "Wage run must be Approved before marking paid."))
            # Find a labor CBS line on this project
            cbs = self.env["buruuj.cbs"].search([
                ("project_id", "=", rec.project_id.id),
                ("cost_type", "=", "labor"),
                ("is_leaf", "=", True),
            ], limit=1)
            if cbs:
                cost_entry = self.env["buruuj.cost.entry"]._record_from_source(
                    rec, cbs.id, "actual", rec.gross_wages,
                    name=f"Wages: {rec.period_label}",
                    ref=rec.name, date=rec.period_end,
                )
                rec.cost_entry_id = cost_entry.id if cost_entry else False
            rec.state = "paid"

    def action_cancel(self):
        for rec in self:
            if rec.state == "paid":
                raise UserError(_(
                    "Cannot cancel a paid wage run."))
            # Release timesheets from this run
            rec.line_ids.write({})  # noop, just to load
            ts = self.env["buruuj.timesheet"].search([
                ("wage_run_id", "=", rec.id),
            ])
            ts.write({"wage_run_id": False, "state": "approved"})
            rec.line_ids.unlink()
            rec.state = "cancelled"

    def action_view_lines(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Wage Lines"),
            "res_model": "buruuj.wage.run.line",
            "view_mode": "list,form",
            "domain": [("wage_run_id", "=", self.id)],
        }


class BuruujWageRunLine(models.Model):
    """One line per worker in a wage run."""
    _name = "buruuj.wage.run.line"
    _description = "Wage Run Line"
    _order = "wage_run_id, worker_id"

    wage_run_id = fields.Many2one("buruuj.wage.run", required=True,
                                     ondelete="cascade")
    project_id = fields.Many2one(related="wage_run_id.project_id", store=True)
    worker_id = fields.Many2one("buruuj.worker", required=True)
    trade_id = fields.Many2one(related="worker_id.trade_id", store=True)
    employment_type = fields.Selection(related="worker_id.employment_type",
                                          store=True)

    regular_hours = fields.Float()
    overtime_hours = fields.Float()
    regular_cost = fields.Monetary()
    overtime_cost = fields.Monetary()
    gross = fields.Monetary(compute="_compute_amounts", store=True)

    allowance_ids = fields.One2many("buruuj.wage.run.allowance", "line_id")
    total_allowances = fields.Monetary(compute="_compute_amounts", store=True)
    total_deductions = fields.Monetary(compute="_compute_amounts", store=True)
    net = fields.Monetary(compute="_compute_amounts", store=True)

    paid_to_subcontractor = fields.Boolean(
        compute="_compute_paid_to_subcontractor", store=True,
        help="True if this is subcontractor labor — pay rolls into the subcontractor's IPC, not directly to the worker.")

    notes = fields.Char()
    currency_id = fields.Many2one(
        "res.currency", related="wage_run_id.currency_id", store=True)
    company_id = fields.Many2one(related="wage_run_id.company_id", store=True)

    @api.depends("regular_cost", "overtime_cost",
                 "allowance_ids.amount", "allowance_ids.direction")
    def _compute_amounts(self):
        for rec in self:
            rec.gross = rec.regular_cost + rec.overtime_cost
            additions = sum(rec.allowance_ids.filtered(
                lambda a: a.direction == "addition").mapped("amount"))
            deductions = sum(rec.allowance_ids.filtered(
                lambda a: a.direction == "deduction").mapped("amount"))
            rec.total_allowances = additions
            rec.total_deductions = deductions
            rec.net = rec.gross + additions - deductions

    @api.depends("worker_id.employment_type")
    def _compute_paid_to_subcontractor(self):
        for rec in self:
            rec.paid_to_subcontractor = (
                rec.worker_id.employment_type == "subcontractor")


class BuruujWageRunAllowance(models.Model):
    """Allowance or deduction line on a wage run line."""
    _name = "buruuj.wage.run.allowance"
    _description = "Wage Allowance / Deduction"

    line_id = fields.Many2one("buruuj.wage.run.line", required=True,
                                 ondelete="cascade")
    type_id = fields.Many2one("buruuj.allowance.type", required=True)
    direction = fields.Selection(related="type_id.direction", store=True)
    amount = fields.Monetary(required=True)
    notes = fields.Char()
    currency_id = fields.Many2one(
        "res.currency", related="line_id.currency_id", store=True)
