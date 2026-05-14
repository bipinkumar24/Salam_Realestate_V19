# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class BuruujIncident(models.Model):
    _name = 'buruuj.hse.incident'
    _description = 'HSE Incident'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date desc, id desc'

    name = fields.Char(copy=False, default=lambda s: _('New'), tracking=True)
    title = fields.Char(required=True)
    project_id = fields.Many2one('project.project', required=True, tracking=True)
    date = fields.Datetime(default=fields.Datetime.now, required=True, tracking=True)
    location = fields.Char()
    type = fields.Selection([
        ('near_miss', 'Near Miss'),
        ('first_aid', 'First Aid Case'),
        ('mtc', 'Medical Treatment Case'),
        ('lti', 'Lost Time Injury'),
        ('fatality', 'Fatality'),
        ('property', 'Property Damage'),
        ('environmental', 'Environmental'),
    ], required=True, tracking=True)
    severity = fields.Selection([
        ('low', 'Low'), ('medium', 'Medium'),
        ('high', 'High'), ('critical', 'Critical'),
    ], default='low', tracking=True)
    persons_involved = fields.Text()
    description = fields.Html(string='Incident Description')
    immediate_action = fields.Html()
    root_cause = fields.Html()
    corrective_action = fields.Html()
    preventive_action = fields.Html()
    reported_by = fields.Many2one('res.users', default=lambda s: s.env.user)
    investigated_by = fields.Many2one('res.users')
    target_close_date = fields.Date()
    closed_date = fields.Date()
    state = fields.Selection([
        ('draft', 'Reported'),
        ('investigating', 'Under Investigation'),
        ('action_pending', 'Action Pending'),
        ('closed', 'Closed'),
    ], default='draft', tracking=True)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'buruuj.hse.incident') or _('New')
        return super().create(vals_list)

    def action_investigate(self):
        self.state = 'investigating'

    def action_pending_action(self):
        self.state = 'action_pending'

    def action_close(self):
        self.write({'state': 'closed',
                    'closed_date': fields.Date.context_today(self)})
