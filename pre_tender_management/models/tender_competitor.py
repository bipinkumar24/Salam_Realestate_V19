# -*- coding: utf-8 -*-
from odoo import fields, models


class TenderCompetitor(models.Model):
    _name = 'tender.competitor'
    _description = 'Competitor Profile'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'name'

    name = fields.Char(required=True)
    partner_id = fields.Many2one(
        'res.partner', string='Company Record',
        domain="[('is_company', '=', True)]",
    )
    sector_ids = fields.Many2many(
        'res.partner.industry', string='Sectors',
    )
    country_ids = fields.Many2many(
        'res.country', 'tender_competitor_country_rel',
        'competitor_id', 'country_id', string='Active Countries',
    )
    strengths = fields.Html()
    weaknesses = fields.Html()
    typical_win_themes = fields.Text(
        help='Themes this competitor is known to use against us.',
    )
    typical_pricing = fields.Text(
        string='Pricing Behaviour',
        help='Discount profile, last known unit prices, financing tactics.',
    )
    past_award_ids = fields.One2many(
        'tender.competitor.past.award', 'competitor_id', string='Past Awards',
    )
    swot_id = fields.Many2one('tender.swot', string='SWOT', ondelete='set null')
    notes = fields.Text()
    company_id = fields.Many2one(
        'res.company', default=lambda self: self.env.company,
    )


class TenderCompetitorPastAward(models.Model):
    _name = 'tender.competitor.past.award'
    _description = 'Competitor Past Award'
    _order = 'award_date desc'

    competitor_id = fields.Many2one(
        'tender.competitor', required=True, ondelete='cascade', index=True,
    )
    project_name = fields.Char(required=True)
    client_id = fields.Many2one('res.partner', string='Client')
    award_date = fields.Date()
    award_value = fields.Monetary(currency_field='currency_id')
    currency_id = fields.Many2one(
        'res.currency', default=lambda s: s.env.company.currency_id,
    )
    win_themes = fields.Text()
    source = fields.Char(help='Where the data came from (TED, press, etc.)')


class TenderSwot(models.Model):
    _name = 'tender.swot'
    _description = 'SWOT Analysis'

    name = fields.Char(required=True, default='SWOT')
    opportunity_id = fields.Many2one(
        'crm.lead', string='Opportunity', ondelete='cascade', index=True,
    )
    competitor_id = fields.Many2one(
        'tender.competitor', string='Competitor', ondelete='cascade', index=True,
    )
    strengths = fields.Html()
    weaknesses = fields.Html()
    opportunities = fields.Html()
    threats = fields.Html()


class TenderOpportunityCompetitor(models.Model):
    _name = 'tender.opportunity.competitor'
    _description = 'Opportunity-Competitor Link'
    _order = 'estimated_pwin desc'

    opportunity_id = fields.Many2one(
        'crm.lead', string='Opportunity', required=True,
        ondelete='cascade', index=True,
    )
    competitor_id = fields.Many2one(
        'tender.competitor', required=True, ondelete='cascade', index=True,
    )
    estimated_pwin = fields.Float(string='Estimated Pwin %')
    is_incumbent = fields.Boolean()
    threat_level = fields.Selection([
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('critical', 'Critical'),
    ], default='medium')
    notes = fields.Text()
