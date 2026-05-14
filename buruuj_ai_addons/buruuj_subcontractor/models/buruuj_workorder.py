# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class BuruujWorkOrder(models.Model):
    """Work Order issued against an active subcontract."""
    _name = 'buruuj.workorder'
    _description = 'Subcontractor Work Order'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date desc, id desc'

    name = fields.Char(copy=False, default=lambda s: _('New'), tracking=True)
    title = fields.Char(required=True)
    subcontract_id = fields.Many2one('buruuj.subcontract', required=True,
                                      ondelete='restrict', tracking=True)
    project_id = fields.Many2one(
        'project.project', related='subcontract_id.project_id', store=True)
    partner_id = fields.Many2one(
        'res.partner', related='subcontract_id.partner_id', store=True)
    date = fields.Date(default=fields.Date.context_today)
    start_date = fields.Date()
    end_date = fields.Date()
    description = fields.Html()
    location = fields.Char(string='Work Location')
    amount = fields.Monetary()
    currency_id = fields.Many2one(
        related='subcontract_id.currency_id', store=True)
    progress = fields.Float(string='Progress %', tracking=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('issued', 'Issued'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('signed_off', 'Signed Off'),
        ('cancelled', 'Cancelled'),
    ], default='draft', tracking=True)
    signed_off_by = fields.Many2one('res.users', string='Signed Off By')
    sign_off_date = fields.Date()

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'buruuj.work.order') or _('New')
        return super().create(vals_list)

    def action_issue(self):
        self.state = 'issued'

    def action_start(self):
        self.state = 'in_progress'

    def action_complete(self):
        self.state = 'completed'

    def action_sign_off(self):
        self.write({
            'state': 'signed_off',
            'signed_off_by': self.env.user.id,
            'sign_off_date': fields.Date.context_today(self),
        })

    def action_cancel(self):
        self.state = 'cancelled'
