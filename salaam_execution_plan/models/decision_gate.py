from odoo import fields, models


class DecisionGate(models.Model):
    _name = "salaam.execution.decision.gate"
    _description = "Salaam Execution Plan: Decision Gate"
    _order = "sequence, id"
    _inherit = ["mail.thread", "mail.activity.mixin"]

    name = fields.Char(required=True, tracking=True)
    gate_number = fields.Integer(string="Gate #", default=0, tracking=True)
    sequence = fields.Integer(default=10)
    lot_id = fields.Many2one(
        "salaam.execution.lot", string="Lot", required=True, ondelete="cascade"
    )
    phase_id = fields.Many2one(
        "salaam.execution.phase",
        related="lot_id.phase_id",
        store=True,
        readonly=True,
        string="Phase",
    )
    state = fields.Selection(
        [
            ("pending", "Pending"),
            ("under_review", "Under Review"),
            ("approved", "Approved"),
            ("rejected", "Rejected"),
        ],
        default="pending",
        tracking=True,
        required=True,
    )
    target_date = fields.Date(tracking=True)
    decision_date = fields.Date(tracking=True)
    note = fields.Html()
    company_id = fields.Many2one(
        "res.company", default=lambda self: self.env.company, required=True
    )
