# -*- coding: utf-8 -*-
from odoo import fields, models


class TenderKickoffGate(models.Model):
    _name = 'tender.kickoff.gate'
    _description = 'Bid Plan Review Gate (Pink/Red/Gold)'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'gate_date'

    name = fields.Char(required=True, default='Review Gate')
    opportunity_id = fields.Many2one(
        'crm.lead', string='Opportunity', required=True,
        ondelete='cascade', index=True, tracking=True,
    )
    gate_type = fields.Selection([
        ('kickoff', 'Bid Kickoff'),
        ('pink', 'Pink Team Review'),
        ('red', 'Red Team Review'),
        ('gold', 'Gold Team Review'),
        ('release', 'Submission Release'),
    ], required=True, default='kickoff', tracking=True)
    gate_date = fields.Datetime(required=True, tracking=True)
    chairperson_id = fields.Many2one('res.users', string='Chairperson')
    attendee_ids = fields.Many2many('res.users', string='Attendees')
    decision = fields.Selection([
        ('proceed', 'Proceed'),
        ('proceed_with_conditions', 'Proceed With Conditions'),
        ('rework', 'Rework Required'),
        ('halt', 'Halt'),
    ], tracking=True)
    decision_notes = fields.Html()
    action_item_ids = fields.One2many(
        'tender.kickoff.gate.action', 'gate_id', string='Action Items',
    )
    state = fields.Selection([
        ('planned', 'Planned'),
        ('held', 'Held'),
        ('cancelled', 'Cancelled'),
    ], default='planned', tracking=True)
    company_id = fields.Many2one(
        'res.company', related='opportunity_id.company_id',
        store=True, readonly=True,
    )


class TenderKickoffGateAction(models.Model):
    _name = 'tender.kickoff.gate.action'
    _description = 'Gate Action Item'
    _order = 'deadline, sequence'

    sequence = fields.Integer(default=10)
    gate_id = fields.Many2one(
        'tender.kickoff.gate', required=True, ondelete='cascade', index=True,
    )
    description = fields.Char(required=True)
    owner_id = fields.Many2one('res.users', string='Owner')
    deadline = fields.Date()
    state = fields.Selection([
        ('open', 'Open'),
        ('done', 'Done'),
        ('cancelled', 'Cancelled'),
    ], default='open')
