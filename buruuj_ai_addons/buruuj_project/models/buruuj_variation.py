# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class BuruujVariation(models.Model):
    """Variation / Change Order."""
    _name = 'buruuj.variation'
    _description = 'Variation Order'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date desc'

    name = fields.Char(string='VO Reference', copy=False, default=lambda s: _('New'))
    title = fields.Char(string='Title', required=True, tracking=True)
    project_id = fields.Many2one('project.project', required=True, ondelete='cascade')
    date = fields.Date(default=fields.Date.context_today, tracking=True)
    initiated_by = fields.Selection([
        ('client', 'Client'),
        ('consultant', 'Consultant'),
        ('contractor', 'Contractor'),
    ], default='client', tracking=True)
    description = fields.Html(string='Description of Change')
    cost_impact = fields.Monetary(string='Cost Impact')
    time_impact_days = fields.Integer(string='Time Impact (days)')
    amount = fields.Monetary(string='VO Amount', tracking=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('submitted', 'Submitted to Client'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('cancelled', 'Cancelled'),
    ], default='draft', tracking=True)
    approval_ref = fields.Char(string='Client Approval Reference')
    approval_date = fields.Date()
    currency_id = fields.Many2one(
        'res.currency', default=lambda self: self.env.company.currency_id)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'buruuj.variation') or _('New')
        return super().create(vals_list)

    def action_submit(self):
        self.state = 'submitted'

    def action_approve(self):
        self.state = 'approved'
        self.approval_date = fields.Date.context_today(self)

    def action_reject(self):
        self.state = 'rejected'

    def action_cancel(self):
        self.state = 'cancelled'

    def action_reset(self):
        self.state = 'draft'
