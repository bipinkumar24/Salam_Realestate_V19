# -*- coding: utf-8 -*-
from odoo import models, fields, api


class BuruujPhase(models.Model):
    _name = 'buruuj.phase'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Project Phase'
    _order = 'sequence, id'

    name = fields.Char(string='Phase Name', required=True)
    code = fields.Char(string='Code')
    sequence = fields.Integer(default=10)
    project_id = fields.Many2one('project.project', required=True, ondelete='cascade')
    planned_start = fields.Date(string='Planned Start')
    planned_end = fields.Date(string='Planned End')
    actual_start = fields.Date()
    actual_end = fields.Date()
    progress = fields.Float(string='Progress %')
    weight_percent = fields.Float(string='Weight %',
                                   help='Used to compute weighted project progress.')
    state = fields.Selection([
        ('not_started', 'Not Started'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('on_hold', 'On Hold'),
    ], default='not_started')
    notes = fields.Text()
