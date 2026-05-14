# -*- coding: utf-8 -*-
from odoo import models, fields, api


class BuruujCostCategory(models.Model):
    """Cost category — top-level classification used across all projects."""
    _name = "buruuj.cost.category"
    _description = "Cost Category"
    _order = "sequence, code"

    name = fields.Char(required=True, translate=True)
    code = fields.Char(required=True, size=10)
    sequence = fields.Integer(default=10)
    cost_type = fields.Selection([
        ("direct_material", "Direct Material"),
        ("subcontract", "Subcontract"),
        ("labor", "Direct Labor"),
        ("plant", "Plant & Equipment"),
        ("rental", "Equipment Rental"),
        ("site_overhead", "Site Overhead"),
        ("indirect", "Indirect / Head Office"),
        ("other", "Other"),
    ], required=True)
    description = fields.Text()
    active = fields.Boolean(default=True)
    company_id = fields.Many2one("res.company",
                                   default=lambda s: s.env.company)

    _sql_constraints = [
        ("code_unique", "unique(code, company_id)",
         "Cost category code must be unique."),
    ]

    @api.depends("name", "code")
    def _compute_display_name(self):
        for rec in self:
            rec.display_name = f"[{rec.code}] {rec.name}" if rec.code else rec.name
