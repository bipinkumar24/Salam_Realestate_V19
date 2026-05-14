# -*- coding: utf-8 -*-
from odoo import fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    is_tender_client = fields.Boolean(string='Issuing Entity')
    is_competitor = fields.Boolean(string='Competitor')
    is_subcontractor = fields.Boolean(string='Subcontractor / JV Partner')
    bid_partner_rating = fields.Selection([
        ('1', '1 — Poor'),
        ('2', '2 — Below Average'),
        ('3', '3 — Average'),
        ('4', '4 — Good'),
        ('5', '5 — Excellent'),
    ], string='Bid Partner Rating')
