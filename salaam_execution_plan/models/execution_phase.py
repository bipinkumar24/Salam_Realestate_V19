from odoo import fields, models


class ExecutionPhase(models.Model):
    _name = "salaam.execution.phase"
    _description = "Salaam Execution Phase"
    _order = "sequence, id"
    _inherit = ["mail.thread", "mail.activity.mixin"]

    name = fields.Char(required=True, tracking=True)
    code = fields.Char(tracking=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    lot_ids = fields.One2many("salaam.execution.lot", "phase_id", string="Lots")
    company_id = fields.Many2one(
        "res.company", default=lambda self: self.env.company, required=True
    )
