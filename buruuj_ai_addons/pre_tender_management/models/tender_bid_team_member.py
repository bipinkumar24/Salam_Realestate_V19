# -*- coding: utf-8 -*-
from odoo import fields, models


class TenderBidTeamMember(models.Model):
    _name = 'tender.bid.team.member'
    _description = 'Bid Team Member'
    _order = 'role, id'

    opportunity_id = fields.Many2one(
        'crm.lead', string='Opportunity', required=True,
        ondelete='cascade', index=True,
    )
    employee_id = fields.Many2one('hr.employee', string='Employee', required=True)
    role = fields.Selection([
        ('bid_manager', 'Bid Manager'),
        ('capture_lead', 'Capture Lead'),
        ('proposal_manager', 'Proposal Manager'),
        ('technical_lead', 'Technical Lead'),
        ('commercial_lead', 'Commercial / Pricing Lead'),
        ('legal_lead', 'Legal Lead'),
        ('estimator', 'Estimator'),
        ('subject_matter_expert', 'Subject Matter Expert'),
        ('reviewer', 'Reviewer'),
        ('signer', 'Authorised Signatory'),
    ], required=True, default='subject_matter_expert')
    allocation_pct = fields.Float(string='Allocation %', default=50.0)
    start_date = fields.Date()
    end_date = fields.Date()
    is_key_personnel = fields.Boolean(
        string='Key Personnel for Submission',
        help='Listed as key personnel in the proposal.',
    )
    notes = fields.Text()
