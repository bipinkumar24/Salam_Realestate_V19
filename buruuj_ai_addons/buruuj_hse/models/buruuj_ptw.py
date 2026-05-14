# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class BuruujPTW(models.Model):
    _name = 'buruuj.ptw'
    _description = 'Permit to Work'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date desc'

    name = fields.Char(copy=False, default=lambda s: _('New'), tracking=True)
    project_id = fields.Many2one('project.project', required=True)
    type = fields.Selection([
        ('hot_work', 'Hot Work'),
        ('confined_space', 'Confined Space'),
        ('working_at_height', 'Working at Height'),
        ('excavation', 'Excavation'),
        ('lifting', 'Lifting Operation'),
        ('electrical', 'Electrical'),
        ('other', 'Other'),
    ], required=True, tracking=True)
    date = fields.Date(default=fields.Date.context_today, tracking=True)
    valid_from = fields.Datetime()
    valid_to = fields.Datetime()
    location = fields.Char()
    work_description = fields.Html()
    contractor_id = fields.Many2one('res.partner', string='Contractor')
    requested_by = fields.Many2one('res.users', default=lambda s: s.env.user)
    approved_by = fields.Many2one('res.users', string='HSE Officer')
    approved_date = fields.Datetime(readonly=True)

    hazards = fields.Html()
    controls = fields.Html()
    ppe_required = fields.Char(string='PPE Required')

    state = fields.Selection([
        ('draft', 'Draft'),
        ('requested', 'Requested'),
        ('approved', 'Approved'),
        ('active', 'Active'),
        ('closed', 'Closed'),
        ('rejected', 'Rejected'),
    ], default='draft', tracking=True)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'buruuj.ptw') or _('New')
        return super().create(vals_list)

    def action_request(self):
        self.state = 'requested'

    def action_approve(self):
        self.write({
            'state': 'approved',
            'approved_by': self.env.user.id,
            'approved_date': fields.Datetime.now(),
        })

    def action_activate(self):
        self.state = 'active'

    def action_close(self):
        self.state = 'closed'

    def action_reject(self):
        self.state = 'rejected'
