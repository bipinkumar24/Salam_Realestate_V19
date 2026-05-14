# -*- coding: utf-8 -*-
from odoo import models, fields, api


class BuruujSnag(models.Model):
    """Snag list / punch list item."""
    _name = 'buruuj.snag'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Snag List Item'
    _order = 'priority desc, target_date'

    name = fields.Char(required=True)
    project_id = fields.Many2one('project.project', required=True, ondelete='cascade')
    location = fields.Char(string='Location')
    discipline = fields.Selection([
        ('civil', 'Civil'),
        ('arch', 'Architectural'),
        ('mep', 'MEP'),
        ('finish', 'Finishing'),
        ('other', 'Other'),
    ], default='other')
    description = fields.Text()
    priority = fields.Selection([
        ('low', 'Low'), ('normal', 'Normal'),
        ('high', 'High'), ('urgent', 'Urgent'),
    ], default='normal')
    raised_by = fields.Many2one('res.users', default=lambda s: s.env.user)
    raised_date = fields.Date(default=fields.Date.context_today)
    responsible_id = fields.Many2one('res.partner',
                                       string='Responsible Subcontractor')
    target_date = fields.Date()
    closed_date = fields.Date()
    state = fields.Selection([
        ('open', 'Open'),
        ('in_progress', 'In Progress'),
        ('closed', 'Closed'),
        ('rejected', 'Rejected'),
    ], default='open')

    def action_start(self):
        self.state = 'in_progress'

    def action_close(self):
        self.write({'state': 'closed',
                    'closed_date': fields.Date.context_today(self)})

    def action_reject(self):
        self.state = 'rejected'
