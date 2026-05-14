# -*- coding: utf-8 -*-
from odoo import api, fields, models


class TenderBidDecision(models.Model):
    _name = 'tender.bid.decision'
    _description = 'Bid / No-Bid Decision'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'decision_date desc, id desc'

    name = fields.Char(required=True, default='New', copy=False, readonly=True)
    opportunity_id = fields.Many2one(
        'crm.lead', string='Opportunity', required=True,
        ondelete='cascade', index=True, tracking=True,
    )
    decision_date = fields.Date(default=fields.Date.context_today, tracking=True)
    decision = fields.Selection([
        ('bid', 'Bid'),
        ('no_bid', 'No Bid'),
        ('conditional', 'Conditional Bid'),
    ], required=True, default='bid', tracking=True)

    score_capability = fields.Float(string='Capability', default=0.0)
    score_capacity = fields.Float(string='Capacity', default=0.0)
    score_profit = fields.Float(string='Profit Potential', default=0.0)
    score_risk = fields.Float(string='Risk (inverse)', default=0.0)
    score_strategic = fields.Float(string='Strategic Value', default=0.0)
    total_score = fields.Float(compute='_compute_total_score', store=True, tracking=True)

    cost_of_bid = fields.Monetary(string='Cost of Bid', currency_field='currency_id')
    expected_return = fields.Monetary(string='Expected Return', currency_field='currency_id')
    currency_id = fields.Many2one(
        'res.currency', related='opportunity_id.company_currency',
        store=True, readonly=True,
    )

    approver_id = fields.Many2one('res.users', string='Approver', tracking=True)
    rationale = fields.Text(string='Rationale')
    approval_request_id = fields.Many2one(
        'approval.request', string='Approval Request', readonly=True, copy=False,
    )

    state = fields.Selection([
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ], default='draft', tracking=True)
    company_id = fields.Many2one(
        'res.company', related='opportunity_id.company_id',
        store=True, readonly=True,
    )

    @api.depends(
        'score_capability', 'score_capacity', 'score_profit',
        'score_risk', 'score_strategic',
    )
    def _compute_total_score(self):
        for rec in self:
            rec.total_score = (
                rec.score_capability + rec.score_capacity + rec.score_profit
                + rec.score_risk + rec.score_strategic
            )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('tender.bid.decision') or 'BD/0001'
        return super().create(vals_list)

    def action_submit(self):
        self.write({'state': 'submitted'})

    def action_approve(self):
        self.write({'state': 'approved'})

    def action_reject(self):
        self.write({'state': 'rejected'})

    def action_reset(self):
        self.write({'state': 'draft'})
