# -*- coding: utf-8 -*-
from odoo import models, fields, api


class ResPartner(models.Model):
    _inherit = 'res.partner'

    # Classification flags
    is_subcontractor = fields.Boolean(string='Is a Subcontractor')
    is_consultant = fields.Boolean(string='Is a Consultant')
    is_client = fields.Boolean(string='Is a Project Client')

    # Construction-specific identifiers
    trade_license_no = fields.Char(string='Trade License No.')
    trade_license_expiry = fields.Date(string='Trade License Expiry')
    tax_card_no = fields.Char(string='Tax Card No.')
    chamber_of_commerce_no = fields.Char(string='Chamber of Commerce No.')

    # Trades performed (for subcontractors)
    trade_ids = fields.Many2many(
        'buruuj.trade', 'partner_trade_rel', 'partner_id', 'trade_id',
        string='Trades / Specializations')

    # Insurance
    insurance_expiry = fields.Date(string='Insurance Expiry Date')
    workmen_comp_expiry = fields.Date(string="Workmen's Comp Expiry")

    # Performance summary (computed in subcontractor module)
    performance_score = fields.Float(
        string='Performance Score', digits=(3, 2),
        help='Score out of 5.0 — computed from project ratings.')

    @api.depends('name', 'trade_license_no')
    def _compute_display_name(self):
        super()._compute_display_name()
