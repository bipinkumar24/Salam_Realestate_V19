# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class BuruujRentalTimesheet(models.Model):
    """Daily record of working hours and idle hours per rental contract."""
    _name = "buruuj.rental.timesheet"
    _description = "Rental Daily Timesheet"
    _order = "date desc, id desc"

    contract_id = fields.Many2one("buruuj.rental.contract", required=True,
                                    ondelete="cascade")
    project_id = fields.Many2one(related="contract_id.project_id", store=True)
    vendor_id = fields.Many2one(related="contract_id.vendor_id", store=True)
    equipment_description = fields.Char(
        related="contract_id.equipment_description", store=True)
    boq_line_id = fields.Many2one(
        "buruuj.boq.line", string="BOQ Item",
        domain="[('boq_id.project_id', '=', project_id)]",
        help="Override the contract's default BOQ line if today's work "
             "served a different scope item.")

    date = fields.Date(required=True, default=fields.Date.context_today)
    working_hours = fields.Float(string="Working Hours", default=0.0)
    idle_hours = fields.Float(string="Idle / Standby Hours", default=0.0)
    breakdown_hours = fields.Float(string="Breakdown Hours", default=0.0,
                                     help="Hours when equipment was not usable. "
                                          "Usually not chargeable to Buruuj.")
    operator_name = fields.Char()
    fuel_consumed_liters = fields.Float(string="Fuel Consumed (L)")
    fuel_supplied_by = fields.Selection([
        ("hirer", "Hirer (Buruuj)"),
        ("vendor", "Vendor on Account"),
    ], default="hirer")
    work_description = fields.Char(string="Work Done")
    captured_by = fields.Many2one("res.users", default=lambda s: s.env.user)
    notes = fields.Text()

    _sql_constraints = [
        ("date_contract_unique", "unique(date, contract_id)",
         "Only one timesheet per contract per day."),
    ]
