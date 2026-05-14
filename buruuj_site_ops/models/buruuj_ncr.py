# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class BuruujNCR(models.Model):
    """Non-Conformance Report — quality issue tracking."""
    _name = 'buruuj.ncr'
    _description = 'Non-Conformance Report'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date desc, id desc'

    name = fields.Char(copy=False, default=lambda s: _('New'), tracking=True)
    title = fields.Char(required=True)
    project_id = fields.Many2one('project.project', required=True, tracking=True)
    date = fields.Date(default=fields.Date.context_today, tracking=True)
    raised_by = fields.Many2one('res.users', default=lambda s: s.env.user)
    responsible_partner_id = fields.Many2one(
        'res.partner', string='Responsible Subcontractor',
        domain=[('is_subcontractor', '=', True)])

    severity = fields.Selection([
        ('minor', 'Minor'),
        ('major', 'Major'),
        ('critical', 'Critical'),
    ], default='minor', tracking=True)
    location = fields.Char(string='Site Location')
    description = fields.Html(string='Non-Conformance Description')
    root_cause = fields.Html()
    corrective_action = fields.Html()
    preventive_action = fields.Html()
    target_close_date = fields.Date()
    closed_date = fields.Date()

    state = fields.Selection([
        ('draft', 'Draft'),
        ('issued', 'Issued'),
        ('action_in_progress', 'Action In Progress'),
        ('closed', 'Closed'),
        ('rejected', 'Rejected'),
    ], default='draft', tracking=True)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'buruuj.ncr') or _('New')
        return super().create(vals_list)

    def action_issue(self):
        self.state = 'issued'

    def action_start_action(self):
        self.state = 'action_in_progress'

    def action_close(self):
        self.write({'state': 'closed',
                    'closed_date': fields.Date.context_today(self)})

    def action_reject(self):
        self.state = 'rejected'
