# -*- coding: utf-8 -*-
from odoo import models, fields, api


class BuruujMilestone(models.Model):
    """Project milestone, used for milestone-based billing."""
    _name = 'buruuj.milestone'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Project Milestone'
    _order = 'planned_date, sequence'

    name = fields.Char(string='Milestone', required=True)
    sequence = fields.Integer(default=10)
    project_id = fields.Many2one('project.project', required=True, ondelete='cascade')
    planned_date = fields.Date(string='Planned Date')
    actual_date = fields.Date(string='Actual Date')
    amount = fields.Monetary(string='Billing Amount')
    percent_of_contract = fields.Float(string='% of Contract')
    state = fields.Selection([
        ('pending', 'Pending'),
        ('achieved', 'Achieved'),
        ('billed', 'Billed'),
        ('paid', 'Paid'),
    ], default='pending')
    description = fields.Text()
    currency_id = fields.Many2one(
        'res.currency', default=lambda self: self.env.company.currency_id)

    def action_mark_achieved(self):
        self.write({'state': 'achieved', 'actual_date': fields.Date.context_today(self)})

    def action_mark_billed(self):
        self.state = 'billed'
