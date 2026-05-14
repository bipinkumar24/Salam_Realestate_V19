# -*- coding: utf-8 -*-
from odoo import models, fields, api


class BuruujVarianceCause(models.Model):
    """Standardised variance cause codes for explaining cost overruns."""
    _name = "buruuj.variance.cause"
    _description = "Variance Cause Code"
    _order = "sequence, code"

    name = fields.Char(required=True, translate=True)
    code = fields.Char(required=True, size=10)
    sequence = fields.Integer(default=10)
    description = fields.Text()
    is_recoverable = fields.Boolean(
        string="Typically Recoverable",
        help="Tick if costs from this cause are usually recoverable from "
             "client (variation), insurance, or subcontractor (back-charge).")
    active = fields.Boolean(default=True)
    company_id = fields.Many2one("res.company",
                                   default=lambda s: s.env.company)

    _sql_constraints = [
        ("code_unique", "unique(code, company_id)",
         "Variance cause code must be unique."),
    ]
