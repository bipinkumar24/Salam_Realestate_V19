# -*- coding: utf-8 -*-
from odoo import models, fields, api


class BuruujITP(models.Model):
    """Inspection Test Plan / Inspection Request."""
    _name = 'buruuj.itp'
    _description = 'Inspection Test Plan'
    _inherit = ['mail.thread']
    _order = 'date desc'

    name = fields.Char(required=True)
    project_id = fields.Many2one('project.project', required=True)
    date = fields.Date(default=fields.Date.context_today)
    activity = fields.Char(string='Activity / Element')
    location = fields.Char()
    requested_by = fields.Many2one('res.users', default=lambda s: s.env.user)
    inspected_by = fields.Many2one('res.partner', string='Consultant')
    inspection_date = fields.Datetime()

    checklist_ids = fields.One2many('buruuj.itp.line', 'itp_id', string='Checklist')

    result = fields.Selection([
        ('pass', 'Passed'),
        ('pass_observation', 'Passed with Observations'),
        ('fail', 'Failed'),
    ])
    state = fields.Selection([
        ('draft', 'Draft'),
        ('requested', 'Requested'),
        ('inspected', 'Inspected'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ], default='draft', tracking=True)
    signed_off_by = fields.Many2one('res.users', readonly=True)
    sign_off_date = fields.Datetime(readonly=True)

    def action_request(self):
        self.state = 'requested'

    def action_inspect(self):
        self.state = 'inspected'

    def action_approve(self):
        self.write({
            'state': 'approved',
            'signed_off_by': self.env.user.id,
            'sign_off_date': fields.Datetime.now(),
        })

    def action_reject(self):
        self.state = 'rejected'


class BuruujITPLine(models.Model):
    _name = 'buruuj.itp.line'
    _description = 'ITP Checklist Item'
    _order = 'sequence, id'

    sequence = fields.Integer(default=10)
    itp_id = fields.Many2one('buruuj.itp', required=True, ondelete='cascade')
    name = fields.Char(string='Check Item', required=True)
    expected = fields.Char(string='Expected / Specification')
    actual = fields.Char(string='Actual')
    result = fields.Selection([
        ('pass', 'Pass'),
        ('fail', 'Fail'),
        ('na', 'N/A'),
    ])
    notes = fields.Char()
