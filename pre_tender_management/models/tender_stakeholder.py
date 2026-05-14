# -*- coding: utf-8 -*-
from odoo import fields, models


class TenderStakeholder(models.Model):
    _name = 'tender.stakeholder'
    _description = 'Tender Stakeholder'
    _inherit = ['mail.thread']
    _order = 'relationship_strength desc, role'

    opportunity_id = fields.Many2one(
        'crm.lead', string='Opportunity', required=True,
        ondelete='cascade', index=True,
    )
    partner_id = fields.Many2one(
        'res.partner', string='Contact', required=True,
    )
    role = fields.Selection([
        ('decision_maker', 'Decision Maker'),
        ('influencer', 'Influencer'),
        ('evaluator', 'Evaluator'),
        ('gatekeeper', 'Gatekeeper'),
        ('end_user', 'End User'),
        ('coach', 'Internal Coach'),
        ('blocker', 'Blocker'),
    ], required=True, default='influencer')
    organisation_id = fields.Many2one(
        'res.partner', string='Organisation',
        domain="[('is_company', '=', True)]",
    )
    title_position = fields.Char(string='Title / Position')
    relationship_strength = fields.Selection([
        ('1', '1 — Hostile'),
        ('2', '2 — Neutral'),
        ('3', '3 — Receptive'),
        ('4', '4 — Supportive'),
        ('5', '5 — Champion'),
    ], default='3')
    last_contact_date = fields.Date()
    notes = fields.Text()
