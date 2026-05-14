# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class BuruujWorker(models.Model):
    """Site worker register — own employees and subcontractor labor.

    For own employees, related to hr.employee. For subcontractor labor,
    no hr.employee (they're not on Buruuj's payroll) but tracked here for
    attendance, productivity, and HSE compliance."""
    _name = "buruuj.worker"
    _description = "Site Worker"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "code"

    name = fields.Char(string="Full Name", required=True, tracking=True)
    code = fields.Char(string="Worker Code", required=True, copy=False,
                         tracking=True,
                         help="Auto-generated badge / payroll number.")
    employment_type = fields.Selection([
        ("own", "Own Employee"),
        ("subcontractor", "Subcontractor Labor"),
        ("contract", "Direct Hire / Contract"),
    ], required=True, default="own", tracking=True)

    # Linkage
    employee_id = fields.Many2one(
        "hr.employee", string="HR Record",
        help="Linked HR employee record (for own employees only).")
    subcontractor_id = fields.Many2one(
        "res.partner", string="Subcontractor",
        domain=[("is_subcontractor", "=", True)],
        help="If subcontractor labor, the subcontractor partner.")

    trade_id = fields.Many2one("buruuj.labor.trade", required=True,
                                 tracking=True)
    skill_level = fields.Selection(related="trade_id.skill_level", store=True)

    # Personal
    nationality = fields.Char()
    id_type = fields.Selection([
        ("national_id", "National ID"),
        ("iqama", "Iqama / Residence Permit"),
        ("passport", "Passport"),
    ])
    id_number = fields.Char(string="ID Number", tracking=True)
    id_expiry = fields.Date(string="ID Expiry", tracking=True)
    contact_phone = fields.Char()
    emergency_contact = fields.Char()

    # Employment
    hire_date = fields.Date()
    termination_date = fields.Date()
    daily_rate = fields.Monetary(string="Daily Rate")
    hourly_rate = fields.Monetary(string="Hourly Rate")
    overtime_rate_multiplier = fields.Float(string="OT Rate Multiplier",
                                              default=1.5)

    # Current assignment
    current_project_id = fields.Many2one("project.project",
                                            string="Current Project")

    # HSE / certifications
    hse_induction_date = fields.Date(string="HSE Induction Completed")
    safety_card_no = fields.Char(string="Safety Card No.")
    safety_card_expiry = fields.Date()
    medical_fitness_expiry = fields.Date()

    # Activity
    attendance_ids = fields.One2many("buruuj.attendance", "worker_id")
    timesheet_ids = fields.One2many("buruuj.timesheet", "worker_id")
    attendance_count = fields.Integer(compute="_compute_counts")
    timesheet_count = fields.Integer(compute="_compute_counts")
    last_attendance_date = fields.Date(compute="_compute_last_attendance",
                                          store=True)

    state = fields.Selection([
        ("active", "Active"),
        ("on_leave", "On Leave"),
        ("terminated", "Terminated"),
    ], default="active", tracking=True)

    notes = fields.Text()
    active = fields.Boolean(default=True)
    currency_id = fields.Many2one(
        "res.currency", default=lambda s: s.env.company.currency_id)
    company_id = fields.Many2one("res.company",
                                   default=lambda s: s.env.company)

    _sql_constraints = [
        ("code_unique", "unique(code, company_id)",
         "Worker code must be unique."),
    ]

    @api.depends("attendance_ids", "timesheet_ids")
    def _compute_counts(self):
        for rec in self:
            rec.attendance_count = len(rec.attendance_ids)
            rec.timesheet_count = len(rec.timesheet_ids)

    @api.depends("attendance_ids.date")
    def _compute_last_attendance(self):
        for rec in self:
            dates = rec.attendance_ids.mapped("date")
            rec.last_attendance_date = max(dates) if dates else False

    @api.constrains("employment_type", "subcontractor_id")
    def _check_subcontractor(self):
        for rec in self:
            if rec.employment_type == "subcontractor" and not rec.subcontractor_id:
                raise UserError(_(
                    "Subcontractor labor must have a subcontractor specified."))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get("code"):
                vals["code"] = self.env["ir.sequence"].next_by_code(
                    "buruuj.worker") or _("New")
        return super().create(vals_list)

    def action_view_attendance(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Attendance"),
            "res_model": "buruuj.attendance",
            "view_mode": "list,form",
            "domain": [("worker_id", "=", self.id)],
            "context": {"default_worker_id": self.id},
        }

    def action_view_timesheets(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Timesheets"),
            "res_model": "buruuj.timesheet",
            "view_mode": "list,form",
            "domain": [("worker_id", "=", self.id)],
            "context": {"default_worker_id": self.id},
        }
