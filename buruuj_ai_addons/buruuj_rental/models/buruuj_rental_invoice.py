# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class BuruujRentalInvoice(models.Model):
    """Vendor rental invoice — reconciled against captured timesheets."""
    _name = "buruuj.rental.invoice"
    _description = "Rental Vendor Invoice"
    _inherit = ["mail.thread"]
    _order = "invoice_date desc, id desc"

    name = fields.Char(string="Vendor Invoice No.", required=True, tracking=True)
    contract_id = fields.Many2one("buruuj.rental.contract", required=True,
                                    ondelete="cascade", tracking=True)
    project_id = fields.Many2one(related="contract_id.project_id", store=True)
    vendor_id = fields.Many2one(related="contract_id.vendor_id", store=True)

    invoice_date = fields.Date(required=True,
                                 default=fields.Date.context_today, tracking=True)
    period_from = fields.Date(string="Period From", required=True)
    period_to = fields.Date(string="Period To", required=True)
    amount = fields.Monetary(string="Vendor Invoice Amount", required=True,
                               tracking=True)

    # Reconciliation against our timesheets
    expected_amount = fields.Monetary(
        compute="_compute_expected", store=True,
        help="What our timesheet records imply we should pay for this period.")
    variance = fields.Monetary(
        compute="_compute_expected", store=True,
        help="Vendor invoice amount minus our expected amount. "
             "Positive = vendor charged more than we recorded.")
    variance_percent = fields.Float(
        compute="_compute_expected", store=True,
        help="Variance as percentage of expected amount.")

    # Dispute tracking
    disputed_amount = fields.Monetary(string="Disputed Amount", default=0.0)
    dispute_reason = fields.Text()

    invoice_attachment = fields.Binary(string="Vendor Invoice (PDF)")
    invoice_filename = fields.Char()

    state = fields.Selection([
        ("received", "Received"),
        ("under_review", "Under Review"),
        ("approved", "Approved for Payment"),
        ("disputed", "Disputed"),
        ("paid", "Paid"),
        ("rejected", "Rejected"),
    ], default="received", tracking=True)

    currency_id = fields.Many2one(
        "res.currency", default=lambda s: s.env.company.currency_id)

    @api.depends("contract_id", "period_from", "period_to", "amount",
                 "contract_id.timesheet_ids.working_hours",
                 "contract_id.timesheet_ids.idle_hours",
                 "contract_id.timesheet_ids.date",
                 "contract_id.rate_basis",
                 "contract_id.base_rate", "contract_id.idle_rate")
    def _compute_expected(self):
        for rec in self:
            expected = 0.0
            if rec.contract_id and rec.period_from and rec.period_to:
                ts = rec.contract_id.timesheet_ids.filtered(
                    lambda t: rec.period_from <= t.date <= rec.period_to)
                wh = sum(ts.mapped("working_hours"))
                ih = sum(ts.mapped("idle_hours"))
                days = len(ts.filtered(lambda t: t.working_hours > 0 or t.idle_hours > 0))
                basis = rec.contract_id.rate_basis
                rate = rec.contract_id.base_rate
                idle = rec.contract_id.idle_rate
                if basis == "hourly":
                    expected = wh * rate + ih * idle
                elif basis == "daily":
                    expected = days * rate
                elif basis == "weekly":
                    expected = (days / 7.0) * rate
                elif basis == "monthly":
                    expected = (days / 30.0) * rate
            rec.expected_amount = expected
            rec.variance = rec.amount - expected
            rec.variance_percent = (
                (rec.variance / expected * 100.0) if expected else 0.0)

    @api.constrains("period_from", "period_to")
    def _check_dates(self):
        for rec in self:
            if rec.period_to and rec.period_from and rec.period_to < rec.period_from:
                raise UserError(_("Period-to must be on or after period-from."))

    def action_review(self):
        self.state = "under_review"

    def action_approve(self):
        self.state = "approved"

    def action_dispute(self):
        for rec in self:
            if not rec.dispute_reason:
                raise UserError(_(
                    "Please enter a dispute reason before marking as disputed."))
            rec.state = "disputed"

    def action_mark_paid(self):
        self.state = "paid"

    def action_reject(self):
        self.state = "rejected"
