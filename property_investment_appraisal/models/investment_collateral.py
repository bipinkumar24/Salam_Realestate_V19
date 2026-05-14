# -*- coding: utf-8 -*-
from odoo import api, fields, models


class InvestmentCollateral(models.Model):
    _name = 'property.investment.collateral'
    _description = 'Investment Collateral / Security'
    _order = 'sequence, id'

    sequence = fields.Integer(default=10)
    application_id = fields.Many2one(
        'property.investment.application',
        string='Application',
        ondelete='cascade',
        required=True,
    )
    location = fields.Char(string='House Location / Area')
    title_number = fields.Char(string='TF / Title Number')
    area_sqm = fields.Float(string='Area (m²)', digits=(10, 2))
    market_value_per_sqm = fields.Monetary(
        string='Market Value per m²',
        currency_field='currency_id',
    )
    currency_id = fields.Many2one(
        'res.currency',
        related='application_id.currency_id',
        store=True,
    )
    # Configurable haircut — default 30% per credit policy
    haircut_rate = fields.Float(
        string='Haircut Rate',
        default=0.30,
        help='Forced-sale discount applied to market value. Default = 30%',
    )
    total_market_value = fields.Monetary(
        string='Total Market Value',
        compute='_compute_valuation',
        store=True,
        currency_field='currency_id',
    )
    adjusted_value = fields.Monetary(
        string='Adjusted / Forced Sale Value',
        compute='_compute_valuation',
        store=True,
        currency_field='currency_id',
    )
    notes = fields.Text(string='Notes')

    @api.depends('area_sqm', 'market_value_per_sqm', 'haircut_rate')
    def _compute_valuation(self):
        for rec in self:
            # Total = area × price per m²
            rec.total_market_value = rec.area_sqm * rec.market_value_per_sqm
            # Adjusted = Total × (1 − haircut)
            rec.adjusted_value = rec.total_market_value * (1.0 - rec.haircut_rate)
