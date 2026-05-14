# -*- coding: utf-8 -*-
from odoo import models, fields, api


class BuruujTrade(models.Model):
    """Construction trade / work category master.

    Used to classify subcontractors, BOQ lines, work orders, and labor."""
    _name = 'buruuj.trade'
    _description = 'Construction Trade'
    _order = 'sequence, code'

    name = fields.Char(string='Trade Name', required=True, translate=True)
    code = fields.Char(string='Code', required=True, size=10)
    sequence = fields.Integer(default=10)
    parent_id = fields.Many2one('buruuj.trade', string='Parent Trade', ondelete='restrict')
    child_ids = fields.One2many('buruuj.trade', 'parent_id', string='Sub-trades')
    description = fields.Text(string='Description')
    active = fields.Boolean(default=True)
    company_id = fields.Many2one(
        'res.company', string='Company',
        default=lambda self: self.env.company)

    _sql_constraints = [
        ('code_unique', 'unique(code, company_id)',
         'Trade code must be unique per company.'),
    ]

    @api.depends('name', 'code')
    def _compute_display_name(self):
        for rec in self:
            rec.display_name = f"[{rec.code}] {rec.name}" if rec.code else rec.name
