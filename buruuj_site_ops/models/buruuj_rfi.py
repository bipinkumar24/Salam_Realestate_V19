# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class BuruujRFI(models.Model):
    """Request for Information sent to consultant/client."""
    _name = 'buruuj.rfi'
    _description = 'Request for Information'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date desc, id desc'

    name = fields.Char(copy=False, default=lambda s: _('New'), tracking=True)
    title = fields.Char(required=True, tracking=True)
    project_id = fields.Many2one('project.project', required=True, tracking=True)
    date = fields.Date(default=fields.Date.context_today, tracking=True)
    raised_by = fields.Many2one('res.users', default=lambda s: s.env.user)
    sent_to = fields.Many2one('res.partner', string='Sent To',
                                domain=[('is_consultant', '=', True)])
    discipline = fields.Selection([
        ('arch', 'Architectural'),
        ('struct', 'Structural'),
        ('mep', 'MEP'),
        ('civil', 'Civil'),
        ('other', 'Other'),
    ], default='arch')
    priority = fields.Selection([
        ('low', 'Low'), ('normal', 'Normal'),
        ('high', 'High'), ('urgent', 'Urgent'),
    ], default='normal', tracking=True)
    drawing_ref = fields.Char(string='Drawing Reference')
    spec_ref = fields.Char(string='Specification Reference')

    description = fields.Html(string='Question / Issue')
    proposed_solution = fields.Html()
    response = fields.Html(string='Response from Consultant')
    response_date = fields.Date(tracking=True)
    response_by = fields.Char()
    response_due = fields.Date(string='Response Due By')
    days_open = fields.Integer(compute='_compute_days_open', store=True)

    state = fields.Selection([
        ('draft', 'Draft'),
        ('sent', 'Sent'),
        ('responded', 'Responded'),
        ('closed', 'Closed'),
    ], default='draft', tracking=True)

    @api.depends('date', 'response_date', 'state')
    def _compute_days_open(self):
        from datetime import date
        for rec in self:
            if rec.date:
                end = rec.response_date or date.today()
                rec.days_open = (end - rec.date).days
            else:
                rec.days_open = 0

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'buruuj.rfi') or _('New')
        return super().create(vals_list)

    def action_send(self):
        self.state = 'sent'

    def action_respond(self):
        self.write({'state': 'responded',
                    'response_date': fields.Date.context_today(self)})

    def action_close(self):
        self.state = 'closed'

    def action_reset(self):
        self.state = 'draft'
