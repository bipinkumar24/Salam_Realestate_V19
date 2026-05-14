# -*- coding: utf-8 -*-
from odoo import api, fields, models


class TenderRisk(models.Model):
    _name = 'tender.risk'
    _description = 'Tender Risk'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'score desc, id desc'

    name = fields.Char(string='Risk', required=True, tracking=True)
    opportunity_id = fields.Many2one(
        'crm.lead', string='Opportunity', required=True,
        ondelete='cascade', index=True, tracking=True,
    )
    category = fields.Selection([
        ('commercial', 'Commercial'),
        ('technical', 'Technical'),
        ('legal', 'Legal'),
        ('financial', 'Financial'),
        ('delivery', 'Delivery / Schedule'),
        ('hse', 'HSE'),
        ('political', 'Political / Country'),
        ('reputational', 'Reputational'),
    ], required=True, default='commercial', tracking=True)
    description = fields.Text()
    probability = fields.Selection([
        ('1', '1 — Rare'),
        ('2', '2 — Unlikely'),
        ('3', '3 — Possible'),
        ('4', '4 — Likely'),
        ('5', '5 — Almost Certain'),
    ], default='3', required=True, tracking=True)
    impact = fields.Selection([
        ('1', '1 — Negligible'),
        ('2', '2 — Minor'),
        ('3', '3 — Moderate'),
        ('4', '4 — Major'),
        ('5', '5 — Catastrophic'),
    ], default='3', required=True, tracking=True)
    score = fields.Integer(compute='_compute_score', store=True, tracking=True)
    severity = fields.Selection([
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('critical', 'Critical'),
    ], compute='_compute_score', store=True)
    mitigation = fields.Text()
    owner_id = fields.Many2one('res.users', string='Owner', tracking=True)
    target_date = fields.Date()
    reserve_amount = fields.Monetary(currency_field='currency_id')
    currency_id = fields.Many2one(
        'res.currency', related='opportunity_id.company_currency',
        store=True, readonly=True,
    )
    source = fields.Selection([
        ('manual', 'Manually Added'),
        ('survey', 'Site Survey'),
        ('compliance', 'Compliance Matrix'),
        ('competitor', 'Competitor Analysis'),
    ], default='manual')
    survey_line_id = fields.Many2one(
        'tender.site.survey.line', string='From Survey Line',
        ondelete='set null',
    )
    state = fields.Selection([
        ('open', 'Open'),
        ('mitigating', 'Mitigating'),
        ('closed', 'Closed'),
        ('accepted', 'Accepted'),
    ], default='open', tracking=True)
    company_id = fields.Many2one(
        'res.company', related='opportunity_id.company_id',
        store=True, readonly=True,
    )

    @api.depends('probability', 'impact')
    def _compute_score(self):
        for rec in self:
            p = int(rec.probability or 0)
            i = int(rec.impact or 0)
            rec.score = p * i
            if rec.score >= 16:
                rec.severity = 'critical'
            elif rec.score >= 10:
                rec.severity = 'high'
            elif rec.score >= 5:
                rec.severity = 'medium'
            else:
                rec.severity = 'low'
