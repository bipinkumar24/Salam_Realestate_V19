# -*- coding: utf-8 -*-
from odoo import fields, models


class TenderCapturePlan(models.Model):
    _name = 'tender.capture.plan'
    _description = 'Capture Plan'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(required=True, default='Capture Plan', tracking=True)
    opportunity_id = fields.Many2one(
        'crm.lead', string='Opportunity', required=True,
        ondelete='cascade', index=True, tracking=True,
    )
    win_strategy = fields.Html()
    value_proposition = fields.Html()
    ghost_strategy = fields.Html(
        string='Ghost / Counter-Strategy',
        help='Tactics anticipated from competitors and our counter-moves.',
    )
    state = fields.Selection([
        ('draft', 'Draft'),
        ('active', 'Active'),
        ('locked', 'Locked'),
    ], default='draft', tracking=True)
    milestone_ids = fields.One2many(
        'tender.capture.milestone', 'capture_plan_id', string='Milestones',
    )
    win_theme_ids = fields.One2many(
        'tender.win.theme', 'capture_plan_id', string='Win Themes',
    )
    company_id = fields.Many2one(
        'res.company', related='opportunity_id.company_id',
        store=True, readonly=True,
    )

    def action_activate(self):
        self.write({'state': 'active'})

    def action_lock(self):
        self.write({'state': 'locked'})


class TenderCaptureMilestone(models.Model):
    _name = 'tender.capture.milestone'
    _description = 'Capture Plan Milestone'
    _order = 'deadline, sequence'

    sequence = fields.Integer(default=10)
    capture_plan_id = fields.Many2one(
        'tender.capture.plan', required=True, ondelete='cascade', index=True,
    )
    opportunity_id = fields.Many2one(
        related='capture_plan_id.opportunity_id', store=True, index=True,
    )
    name = fields.Char(required=True)
    description = fields.Text()
    owner_id = fields.Many2one('res.users', string='Owner')
    deadline = fields.Date()
    state = fields.Selection([
        ('open', 'Open'),
        ('in_progress', 'In Progress'),
        ('done', 'Done'),
        ('cancelled', 'Cancelled'),
    ], default='open')


class TenderWinTheme(models.Model):
    _name = 'tender.win.theme'
    _description = 'Win Theme / Discriminator'
    _order = 'sequence, id'

    sequence = fields.Integer(default=10)
    capture_plan_id = fields.Many2one(
        'tender.capture.plan', required=True, ondelete='cascade', index=True,
    )
    name = fields.Char(string='Theme', required=True)
    is_discriminator = fields.Boolean(
        help='True discriminator: something only we offer.',
    )
    proof_points = fields.Text()
    addressed_in_volume = fields.Selection([
        ('technical', 'Technical Volume'),
        ('commercial', 'Commercial Volume'),
        ('exec_summary', 'Executive Summary'),
        ('multiple', 'Multiple Volumes'),
    ])
