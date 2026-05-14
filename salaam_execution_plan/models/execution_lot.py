from odoo import fields, models


class ExecutionLot(models.Model):
    _name = "salaam.execution.lot"
    _description = "Salaam Execution Lot"
    _order = "sequence, id"
    _inherit = ["mail.thread", "mail.activity.mixin"]

    name = fields.Char(required=True, tracking=True)
    code = fields.Char(tracking=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    phase_id = fields.Many2one(
        "salaam.execution.phase", string="Phase", required=True, ondelete="cascade"
    )
    gate_ids = fields.One2many(
        "salaam.execution.decision.gate", "lot_id", string="Decision Gates"
    )
    company_id = fields.Many2one(
        "res.company", default=lambda self: self.env.company, required=True
    )
