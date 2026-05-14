# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class BuruujRentalContract(models.Model):
    """Rental contract with a vendor: rates, mob/demob, idle clauses."""
    _name = "buruuj.rental.contract"
    _description = "Rental Contract"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "start_date desc, id desc"

    name = fields.Char(copy=False, default=lambda s: _("New"), tracking=True)
    requisition_id = fields.Many2one("buruuj.rental.requisition",
                                       string="Source Requisition", tracking=True)
    project_id = fields.Many2one("project.project", required=True, tracking=True)
    vendor_id = fields.Many2one(
        "res.partner", string="Rental Vendor", required=True, tracking=True,
        domain=[("supplier_rank", ">", 0)])
    equipment_id = fields.Many2one("buruuj.equipment", string="Equipment",
                                     help="Linked once equipment arrives on site.")
    equipment_description = fields.Char(
        string="Equipment Description", required=True,
        help="Vendor-side description (make, model, capacity).")
    serial_no = fields.Char(string="Vendor Serial / Plate")

    start_date = fields.Date(required=True, tracking=True)
    end_date = fields.Date(string="Planned End Date", required=True, tracking=True)
    actual_off_hire_date = fields.Date(string="Actual Off-Hire Date",
                                          readonly=True, tracking=True)

    # Rates
    rate_basis = fields.Selection([
        ("daily", "Daily"),
        ("weekly", "Weekly"),
        ("monthly", "Monthly"),
        ("hourly", "Hourly"),
    ], default="daily", required=True)
    base_rate = fields.Monetary(string="Base Rate", required=True,
                                  help="Rate per the basis above.")
    idle_rate = fields.Monetary(
        string="Idle / Standby Rate",
        help="Reduced rate when equipment is on site but not in use. "
             "Often a percentage of base rate, but stored as absolute.")
    overtime_rate = fields.Monetary(
        string="Overtime / Extra Hour Rate",
        help="If hourly basis: rate for hours beyond standard shift.")
    minimum_hire_period = fields.Integer(
        string="Minimum Hire Period (days)", default=1,
        help="Vendor will charge for this minimum even if off-hired earlier.")

    # Mob / Demob
    mobilization_cost = fields.Monetary(string="Mobilization Cost")
    demobilization_cost = fields.Monetary(string="Demobilization Cost")

    # Operator / fuel terms
    operator_included = fields.Boolean(string="Operator Included",
                                          default=False)
    operator_name = fields.Char()
    fuel_terms = fields.Selection([
        ("by_hire", "Fuel by Hirer (Buruuj)"),
        ("on_account", "Fuel on Vendor Account"),
        ("daily_allowance", "Daily Fuel Allowance"),
    ], default="by_hire")
    fuel_allowance = fields.Monetary(string="Fuel Allowance")

    # Insurance & liability
    insurance_by = fields.Selection([
        ("vendor", "Vendor"),
        ("hirer", "Hirer (Buruuj)"),
        ("shared", "Shared"),
    ], default="vendor")
    operator_liability = fields.Selection([
        ("vendor", "Vendor"),
        ("hirer", "Hirer (Buruuj)"),
    ], default="vendor")

    # Computed totals
    timesheet_ids = fields.One2many("buruuj.rental.timesheet", "contract_id")
    invoice_ids = fields.One2many("buruuj.rental.invoice", "contract_id")
    total_working_hours = fields.Float(compute="_compute_totals", store=True)
    total_idle_hours = fields.Float(compute="_compute_totals", store=True)
    total_days_on_site = fields.Integer(compute="_compute_totals", store=True)
    estimated_cost = fields.Monetary(compute="_compute_totals", store=True)
    invoiced_amount = fields.Monetary(compute="_compute_invoiced", store=True)
    disputed_amount = fields.Monetary(compute="_compute_invoiced", store=True)

    timesheet_count = fields.Integer(compute="_compute_counts")
    invoice_count = fields.Integer(compute="_compute_counts")

    contract_attachment = fields.Binary(string="Signed Contract (PDF)")
    contract_filename = fields.Char()
    notes = fields.Html()

    state = fields.Selection([
        ("draft", "Draft"),
        ("approved", "Approved"),
        ("active", "Active (On Site)"),
        ("off_hire_pending", "Off-Hire Pending"),
        ("off_hired", "Off-Hired"),
        ("closed", "Closed"),
        ("cancelled", "Cancelled"),
    ], default="draft", tracking=True)

    currency_id = fields.Many2one(
        "res.currency", default=lambda s: s.env.company.currency_id)
    company_id = fields.Many2one("res.company", default=lambda s: s.env.company)

    @api.depends("timesheet_ids.working_hours", "timesheet_ids.idle_hours",
                 "timesheet_ids.date", "rate_basis", "base_rate",
                 "mobilization_cost", "demobilization_cost")
    def _compute_totals(self):
        for rec in self:
            wh = sum(rec.timesheet_ids.mapped("working_hours"))
            ih = sum(rec.timesheet_ids.mapped("idle_hours"))
            days = len(rec.timesheet_ids.filtered(lambda t: t.working_hours > 0
                                                          or t.idle_hours > 0))
            rec.total_working_hours = wh
            rec.total_idle_hours = ih
            rec.total_days_on_site = days

            # Rough estimate of cost based on basis
            cost = rec.mobilization_cost + rec.demobilization_cost
            if rec.rate_basis == "hourly":
                cost += wh * rec.base_rate + ih * rec.idle_rate
            elif rec.rate_basis == "daily":
                cost += days * rec.base_rate
            elif rec.rate_basis == "weekly":
                cost += (days / 7.0) * rec.base_rate
            elif rec.rate_basis == "monthly":
                cost += (days / 30.0) * rec.base_rate
            rec.estimated_cost = cost

    @api.depends("invoice_ids.amount", "invoice_ids.disputed_amount",
                 "invoice_ids.state")
    def _compute_invoiced(self):
        for rec in self:
            rec.invoiced_amount = sum(rec.invoice_ids.filtered(
                lambda i: i.state in ("approved", "paid")).mapped("amount"))
            rec.disputed_amount = sum(rec.invoice_ids.filtered(
                lambda i: i.state == "disputed").mapped("disputed_amount"))

    @api.depends("timesheet_ids", "invoice_ids")
    def _compute_counts(self):
        for rec in self:
            rec.timesheet_count = len(rec.timesheet_ids)
            rec.invoice_count = len(rec.invoice_ids)

    @api.constrains("start_date", "end_date")
    def _check_dates(self):
        for rec in self:
            if rec.end_date and rec.start_date and rec.end_date < rec.start_date:
                raise UserError(_("End date must be on or after start date."))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", _("New")) == _("New"):
                vals["name"] = self.env["ir.sequence"].next_by_code(
                    "buruuj.rental.contract") or _("New")
        contracts = super().create(vals_list)
        for c in contracts:
            if c.requisition_id and c.requisition_id.state == "quoting":
                c.requisition_id.state = "contracted"
        return contracts

    def action_approve(self):
        self.state = "approved"

    def action_activate(self):
        for rec in self:
            if not rec.start_date:
                raise UserError(_("Start date is required."))
            rec.state = "active"

    def action_request_off_hire(self):
        self.state = "off_hire_pending"

    def action_off_hire(self):
        for rec in self:
            rec.write({
                "state": "off_hired",
                "actual_off_hire_date": fields.Date.context_today(self),
            })
            if rec.equipment_id:
                rec.equipment_id.state = "available"

    def action_close(self):
        self.state = "closed"

    def action_cancel(self):
        self.state = "cancelled"

    def action_view_timesheets(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Daily Timesheets"),
            "res_model": "buruuj.rental.timesheet",
            "view_mode": "list,form",
            "domain": [("contract_id", "=", self.id)],
            "context": {"default_contract_id": self.id},
        }

    def action_view_invoices(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Vendor Invoices"),
            "res_model": "buruuj.rental.invoice",
            "view_mode": "list,form",
            "domain": [("contract_id", "=", self.id)],
            "context": {"default_contract_id": self.id},
        }

    @api.model
    def cron_off_hire_alert(self):
        """Daily scan: contracts past planned end date and still active."""
        from datetime import timedelta  # safe in regular Python
        today = fields.Date.context_today(self)
        overdue = self.search([
            ('state', '=', 'active'),
            ('end_date', '<', today),
        ])
        for contract in overdue:
            contract.activity_schedule(
                'mail.mail_activity_data_warning',
                summary='Off-hire decision needed',
                note=(
                    f'Contract {contract.name} planned end was '
                    f'{contract.end_date}. Confirm extension or off-hire.'
                ),
                user_id=contract.create_uid.id,
            )
        return len(overdue)
