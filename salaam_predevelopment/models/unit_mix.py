# -*- coding: utf-8 -*-
from odoo import models, fields, api


class PredevelopmentUnitMix(models.Model):
    """
    Unit mix line: defines how many units of each type
    are planned in a development.
    """
    _name = 'salaam.predevelopment.unit.mix'
    _description = 'Unit Mix Line'
    _order = 'predevelopment_id, sequence'

    predevelopment_id = fields.Many2one(
        'salaam.predevelopment', string='Development',
        required=True, ondelete='cascade',
    )
    sequence = fields.Integer(default=10)

    unit_type = fields.Selection([
        ('studio',      'Studio'),
        ('1br',         '1 Bedroom'),
        ('2br',         '2 Bedroom'),
        ('3br',         '3 Bedroom'),
        ('4br',         '4 Bedroom'),
        ('5br',         '5 Bedroom'),
        ('duplex',      'Duplex'),
        ('penthouse',   'Penthouse'),
        ('villa',       'Villa'),
        ('townhouse',   'Townhouse'),
        ('commercial',  'Commercial'),
        ('retail',      'Retail'),
        ('office',      'Office'),
        ('other',       'Other'),
    ], string='Unit Type', required=True)

    unit_type_code = fields.Char(string='Unit Code', help='e.g. FN3, A1, PH')
    quantity = fields.Integer(string='Quantity', required=True, default=1)
    unit_area = fields.Float(string='Avg Area (m²)')
    sale_price = fields.Monetary(
        string='Indicative Sale Price',
        currency_field='currency_id',
    )
    currency_id = fields.Many2one(
        related='predevelopment_id.currency_id',
        string='Currency',
    )
    total_area = fields.Float(
        string='Total Area (m²)',
        compute='_compute_totals', store=True,
    )
    total_revenue = fields.Monetary(
        string='Total Revenue',
        compute='_compute_totals', store=True,
        currency_field='currency_id',
    )
    notes = fields.Char(string='Notes')

    @api.depends('quantity', 'unit_area', 'sale_price')
    def _compute_totals(self):
        for rec in self:
            rec.total_area = (rec.quantity or 0) * (rec.unit_area or 0)
            rec.total_revenue = (rec.quantity or 0) * (rec.sale_price or 0)


# ── CROSS-MODULE EXTENSIONS ───────────────────────────────────────────────────

class TenderPredevelopmentLink(models.Model):
    """Extends salaam.tender to link back to predevelopment."""
    _inherit = 'salaam.tender'

    predevelopment_id = fields.Many2one(
        'salaam.predevelopment',
        string='Pre-Development',
        index=True,
        help='The pre-development application this tender belongs to',
    )


class PropertyDetailsPredevelopmentLink(models.Model):
    """Extends property.details to link back to predevelopment."""
    _inherit = 'property.details'

    predevelopment_id = fields.Many2one(
        'salaam.predevelopment',
        string='Pre-Development Application',
        index=True,
        help='The pre-development application that created this unit',
    )
