# -*- coding: utf-8 -*-
from odoo import models, fields, api


class BuruujSubmittal(models.Model):
    _name = 'buruuj.submittal'
    _description = 'Material / Product Submittal'
    _inherit = ['mail.thread']
    _order = 'date desc'

    name = fields.Char(required=True)
    project_id = fields.Many2one('project.project', required=True)
    date = fields.Date(default=fields.Date.context_today)
    submittal_type = fields.Selection([
        ('material', 'Material Approval'),
        ('shop_drawing', 'Shop Drawing'),
        ('sample', 'Sample'),
        ('mock_up', 'Mock-up'),
        ('method', 'Method Statement'),
    ], default='material', required=True)
    item = fields.Char(string='Item / Material', required=True)
    manufacturer = fields.Char()
    spec_section = fields.Char(string='Spec Section')
    submitted_to = fields.Many2one('res.partner',
                                     domain=[('is_consultant', '=', True)])
    submitted_by = fields.Many2one('res.users', default=lambda s: s.env.user)
    response_date = fields.Date()
    response = fields.Selection([
        ('approved', 'Approved'),
        ('approved_comments', 'Approved with Comments'),
        ('revise_resubmit', 'Revise & Resubmit'),
        ('rejected', 'Rejected'),
    ])
    state = fields.Selection([
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('responded', 'Responded'),
        ('closed', 'Closed'),
    ], default='draft', tracking=True)
    notes = fields.Html()
    attachment_ids = fields.Many2many('ir.attachment')

    def action_submit(self):
        self.state = 'submitted'

    def action_respond(self):
        self.write({'state': 'responded',
                    'response_date': fields.Date.context_today(self)})

    def action_close(self):
        self.state = 'closed'
