# -*- coding: utf-8 -*-
from odoo import models, fields, api


class BuruujClaim(models.Model):
    _name = 'buruuj.claim'
    _description = 'Construction Claim'
    _inherit = ['mail.thread']
    _order = 'date desc'

    name = fields.Char(required=True)
    project_id = fields.Many2one('project.project', required=True)
    contract_id = fields.Many2one('buruuj.contract')
    type = fields.Selection([
        ('eot', 'Extension of Time (EOT)'),
        ('prolongation', 'Prolongation Cost'),
        ('disruption', 'Disruption'),
        ('variation', 'Variation Disagreement'),
        ('other', 'Other'),
    ], required=True, default='eot', tracking=True)
    direction = fields.Selection([
        ('outgoing', 'We are claiming'),
        ('incoming', 'Claim against us'),
    ], default='outgoing', tracking=True)

    date = fields.Date(default=fields.Date.context_today)
    claim_period_start = fields.Date()
    claim_period_end = fields.Date()
    eot_days = fields.Integer(string='EOT Days Claimed')
    cost_amount = fields.Monetary(string='Cost Claimed')

    description = fields.Html()
    contractual_basis = fields.Html()
    supporting_evidence = fields.Text()

    awarded_days = fields.Integer(string='EOT Days Awarded')
    awarded_amount = fields.Monetary()

    state = fields.Selection([
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('negotiating', 'Under Negotiation'),
        ('awarded', 'Awarded'),
        ('rejected', 'Rejected'),
        ('withdrawn', 'Withdrawn'),
    ], default='draft', tracking=True)

    currency_id = fields.Many2one(
        'res.currency', default=lambda s: s.env.company.currency_id)

    def action_submit(self):
        self.state = 'submitted'

    def action_negotiate(self):
        self.state = 'negotiating'

    def action_award(self):
        self.state = 'awarded'

    def action_reject(self):
        self.state = 'rejected'

    def action_withdraw(self):
        self.state = 'withdrawn'
