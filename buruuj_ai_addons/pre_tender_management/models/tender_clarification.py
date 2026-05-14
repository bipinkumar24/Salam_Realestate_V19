# -*- coding: utf-8 -*-
from odoo import fields, models


class TenderClarification(models.Model):
    _name = 'tender.clarification'
    _description = 'Pre-Bid Clarification Q&A'
    _inherit = ['mail.thread']
    _order = 'asked_date desc'

    opportunity_id = fields.Many2one(
        'crm.lead', string='Opportunity', required=True,
        ondelete='cascade', index=True,
    )
    direction = fields.Selection([
        ('ours', 'Our Question to Client'),
        ('clients', "Client's Clarification"),
        ('addendum', 'Addendum / Amendment'),
    ], required=True, default='ours')
    question = fields.Text(required=True)
    asked_by_id = fields.Many2one('res.users', string='Asked By', default=lambda s: s.env.user)
    asked_date = fields.Date(default=fields.Date.context_today, required=True)
    response_deadline = fields.Date()
    response = fields.Text()
    response_date = fields.Date()
    addendum_reference = fields.Char(string='Addendum Ref.')
    state = fields.Selection([
        ('open', 'Open'),
        ('responded', 'Responded'),
        ('overdue', 'Overdue'),
        ('cancelled', 'Cancelled'),
    ], default='open', tracking=True)
    attachment_ids = fields.Many2many(
        'ir.attachment', 'tender_clarification_attachment_rel',
        'clarification_id', 'attachment_id', string='Attachments',
    )
