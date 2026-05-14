from odoo import fields, models


class IafaoDashboard(models.Model):
    _name = "salaam.iafao.dashboard"
    _description = "Salaam IAFAO Dashboard"
    _order = "sequence, id"

    name = fields.Char(required=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    note = fields.Text()
