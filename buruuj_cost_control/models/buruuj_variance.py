# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class BuruujVariance(models.Model):
    """Cost variance log - explains why FAC differs from budget."""
    _name = "buruuj.variance"
    _description = "Cost Variance Entry"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "date desc, id desc"

    name = fields.Char(string="Description", required=True, tracking=True)
    project_id = fields.Many2one("project.project", required=True,
                                   tracking=True)
    cbs_id = fields.Many2one("buruuj.cbs", string="CBS Line",
                               domain="[('project_id','=',project_id)]")
    cause_id = fields.Many2one("buruuj.variance.cause",
                                 string="Cause Code", required=True,
                                 tracking=True)
    is_recoverable = fields.Boolean(related="cause_id.is_recoverable",
                                       store=True)

    date = fields.Date(default=fields.Date.context_today, required=True)
    amount = fields.Monetary(required=True, tracking=True,
                                help="Positive = saving; negative = overrun.")
    direction = fields.Selection([
        ("overrun", "Overrun"),
        ("saving", "Saving"),
    ], compute="_compute_direction", store=True)

    description = fields.Html()
    corrective_action = fields.Html()

    # Recovery tracking when cause is recoverable
    recovery_status = fields.Selection([
        ("not_applicable", "Not Recoverable"),
        ("identified", "Recovery Identified"),
        ("submitted", "Submitted to Client/Subcontractor"),
        ("approved", "Recovery Approved"),
        ("recovered", "Recovered"),
        ("rejected", "Recovery Rejected"),
    ], default="not_applicable", tracking=True)
    recovery_amount = fields.Monetary(string="Amount Recovered")
    recovery_ref = fields.Char(
        string="Recovery Reference",
        help="VO number, claim ref, back-charge, etc.")

    state = fields.Selection([
        ("draft", "Draft"),
        ("logged", "Logged"),
        ("closed", "Closed"),
    ], default="draft", tracking=True)

    currency_id = fields.Many2one(
        "res.currency",
        default=lambda s: s.env.company.currency_id, store=True)

    @api.depends("amount")
    def _compute_direction(self):
        for rec in self:
            rec.direction = "overrun" if rec.amount < 0 else "saving"

    def action_log(self):
        self.state = "logged"

    def action_close(self):
        self.state = "closed"
