# -*- coding: utf-8 -*-
from odoo import models, fields, api


class BuruujRate(models.Model):
    """Master rate database. Used as a default during BOQ build-up."""
    _name = 'buruuj.rate'
    _description = 'Construction Master Rate'
    _order = 'category, code'

    name = fields.Char(string='Description', required=True)
    code = fields.Char(string='Code', required=True)
    category = fields.Selection([
        ('labor', 'Labor'),
        ('material', 'Material'),
        ('equipment', 'Equipment'),
        ('subcontractor', 'Subcontractor'),
        ('composite', 'Composite Rate'),
    ], required=True, default='material')
    uom_id = fields.Many2one('uom.uom', string='Unit of Measure', required=True)
    trade_id = fields.Many2one('buruuj.trade', string='Trade')
    unit_rate = fields.Monetary(string='Unit Rate', required=True)
    currency_id = fields.Many2one(
        'res.currency', default=lambda self: self.env.company.currency_id)
    valid_from = fields.Date(string='Valid From', default=fields.Date.context_today)
    valid_to = fields.Date(string='Valid To')
    notes = fields.Text(string='Notes')
    active = fields.Boolean(default=True)
    company_id = fields.Many2one(
        'res.company', default=lambda self: self.env.company)

    _sql_constraints = [
        ('code_unique', 'unique(code, company_id)',
         'Rate code must be unique per company.'),
    ]
