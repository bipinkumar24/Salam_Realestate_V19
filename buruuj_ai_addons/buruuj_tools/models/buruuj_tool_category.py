# -*- coding: utf-8 -*-
from odoo import models, fields, api


class BuruujToolCategory(models.Model):
    """Tool category for classification (Power Tools, Hand Tools, Instruments, etc.)."""
    _name = 'buruuj.tool.category'
    _description = 'Tool Category'
    _order = 'sequence, code'

    name = fields.Char(required=True, translate=True)
    code = fields.Char(required=True, size=10)
    sequence = fields.Integer(default=10)
    parent_id = fields.Many2one('buruuj.tool.category', string='Parent', ondelete='restrict')
    child_ids = fields.One2many('buruuj.tool.category', 'parent_id')
    requires_calibration = fields.Boolean(
        string='Requires Calibration',
        help='Tools in this category will be flagged for periodic calibration.')
    is_consumable = fields.Boolean(
        string='Consumable Category',
        help='Items in this category are consumed (drill bits, blades) — not returned.')
    description = fields.Text()
    active = fields.Boolean(default=True)
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)

    _sql_constraints = [
        ('code_unique', 'unique(code, company_id)',
         'Tool category code must be unique per company.'),
    ]

    @api.depends('name', 'code')
    def _compute_display_name(self):
        for rec in self:
            rec.display_name = f"[{rec.code}] {rec.name}" if rec.code else rec.name
