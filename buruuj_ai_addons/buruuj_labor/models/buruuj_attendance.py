# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class BuruujAttendance(models.Model):
    """Daily site attendance for a worker. One row per worker per day per project.

    Captured by foreman or storekeeper at the start of each shift, closed at
    end of shift with hours worked. Forms the basis for timesheet rollup."""
    _name = "buruuj.attendance"
    _description = "Site Attendance"
    _order = "date desc, worker_id"

    worker_id = fields.Many2one("buruuj.worker", required=True,
                                  ondelete="cascade")
    worker_code = fields.Char(related="worker_id.code", store=True)
    trade_id = fields.Many2one(related="worker_id.trade_id", store=True)
    project_id = fields.Many2one("project.project", required=True)
    phase_id = fields.Many2one("buruuj.phase",
                                 domain="[('project_id','=',project_id)]")
    subcontract_id = fields.Many2one(
        "buruuj.subcontract",
        domain="[('project_id','=',project_id)]",
        help="If working under a specific subcontract.")

    date = fields.Date(required=True, default=fields.Date.context_today,
                         index=True)
    status = fields.Selection([
        ("present", "Present"),
        ("absent", "Absent"),
        ("on_leave", "On Approved Leave"),
        ("sick", "Sick"),
        ("no_work", "No Work (weather/holiday)"),
    ], default="present", required=True)

    check_in = fields.Float(string="Check In Time",
                              help="24h decimal time, e.g., 7.5 for 07:30")
    check_out = fields.Float(string="Check Out Time")
    hours_worked = fields.Float(string="Hours Worked",
                                  compute="_compute_hours_worked", store=True,
                                  readonly=False)
    overtime_hours = fields.Float(string="Overtime Hours")

    captured_by = fields.Many2one("res.users",
                                    default=lambda s: s.env.user)
    notes = fields.Char()

    company_id = fields.Many2one("res.company",
                                   default=lambda s: s.env.company)

    _sql_constraints = [
        ("worker_date_project_unique",
         "unique(worker_id, date, project_id)",
         "Only one attendance per worker per day per project."),
    ]

    @api.depends("check_in", "check_out", "status")
    def _compute_hours_worked(self):
        for rec in self:
            if rec.status != "present":
                rec.hours_worked = 0.0
            elif rec.check_in and rec.check_out and rec.check_out > rec.check_in:
                # Naive — doesn't subtract break time. Adjust manually if needed.
                rec.hours_worked = rec.check_out - rec.check_in
            else:
                rec.hours_worked = rec.hours_worked or 0.0
