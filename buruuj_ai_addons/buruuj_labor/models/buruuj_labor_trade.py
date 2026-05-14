# -*- coding: utf-8 -*-
from odoo import models, fields, api


class BuruujLaborTrade(models.Model):
    """Specific labor trades / job titles. Different from buruuj.trade which is
    used for subcontract scope categorisation. Labor trades are individual
    skill categories (mason, electrician, helper, etc.)."""
    _name = "buruuj.labor.trade"
    _description = "Labor Trade"
    _order = "sequence, code"

    name = fields.Char(required=True, translate=True)
    code = fields.Char(required=True, size=10)
    sequence = fields.Integer(default=10)
    skill_level = fields.Selection([
        ("helper", "Helper / Unskilled"),
        ("semi", "Semi-Skilled"),
        ("skilled", "Skilled"),
        ("foreman", "Foreman"),
        ("supervisor", "Supervisor"),
    ], default="skilled")
    typical_daily_rate = fields.Monetary()
    description = fields.Text()
    active = fields.Boolean(default=True)
    currency_id = fields.Many2one(
        "res.currency", default=lambda s: s.env.company.currency_id)
    company_id = fields.Many2one("res.company",
                                   default=lambda s: s.env.company)

    _sql_constraints = [
        ("code_unique", "unique(code, company_id)",
         "Labor trade code must be unique."),
    ]

    @api.depends("name", "code")
    def _compute_display_name(self):
        for rec in self:
            rec.display_name = f"[{rec.code}] {rec.name}" if rec.code else rec.name
