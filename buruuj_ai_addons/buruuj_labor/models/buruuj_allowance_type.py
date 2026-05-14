# -*- coding: utf-8 -*-
from odoo import models, fields, api


class BuruujAllowanceType(models.Model):
    """Allowance / deduction types — overtime, transport, advance recovery, etc."""
    _name = "buruuj.allowance.type"
    _description = "Wage Allowance / Deduction Type"
    _order = "sequence, code"

    name = fields.Char(required=True, translate=True)
    code = fields.Char(required=True, size=10)
    sequence = fields.Integer(default=10)
    direction = fields.Selection([
        ("addition", "Addition (paid to worker)"),
        ("deduction", "Deduction (recovered from worker)"),
    ], required=True, default="addition")
    is_taxable = fields.Boolean(string="Taxable",
                                  help="Subject to income tax / statutory deductions.")
    description = fields.Text()
    active = fields.Boolean(default=True)
    company_id = fields.Many2one("res.company",
                                   default=lambda s: s.env.company)

    _sql_constraints = [
        ("code_unique", "unique(code, company_id)",
         "Allowance type code must be unique."),
    ]
