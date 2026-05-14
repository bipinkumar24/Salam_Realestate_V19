# -*- coding: utf-8 -*-
from odoo import models, fields, api


class BuruujMaterialCategory(models.Model):
    _name = "buruuj.material.category"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = "Material Category"
    _order = "sequence, code"

    name = fields.Char(required=True, translate=True)
    code = fields.Char(required=True, size=10)
    sequence = fields.Integer(default=10)
    parent_id = fields.Many2one("buruuj.material.category",
                                  string="Parent", ondelete="restrict")
    description = fields.Text()
    active = fields.Boolean(default=True)
    company_id = fields.Many2one("res.company",
                                   default=lambda s: s.env.company)

    _sql_constraints = [
        ("code_unique", "unique(code, company_id)",
         "Material category code must be unique."),
    ]

    @api.depends("name", "code")
    def _compute_display_name(self):
        for rec in self:
            rec.display_name = f"[{rec.code}] {rec.name}" if rec.code else rec.name
