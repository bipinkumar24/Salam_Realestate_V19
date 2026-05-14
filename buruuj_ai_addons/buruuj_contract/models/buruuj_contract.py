# -*- coding: utf-8 -*-
from odoo import models, fields, api


class BuruujContract(models.Model):
    _name = 'buruuj.contract'
    _description = 'Master Contract'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date desc'

    name = fields.Char(required=True, tracking=True)
    reference = fields.Char(string='Contract Reference No.', copy=False)
    type = fields.Selection([
        ('client', 'Client Contract'),
        ('subcontract', 'Subcontract'),
        ('supply', 'Supply Contract'),
        ('lease', 'Lease Agreement'),
        ('consultant', 'Consultant Agreement'),
        ('other', 'Other'),
    ], required=True, default='client', tracking=True)
    project_id = fields.Many2one('project.project')
    counterparty_id = fields.Many2one('res.partner', string='Counterparty',
                                        required=True)

    date = fields.Date(default=fields.Date.context_today)
    commencement_date = fields.Date(tracking=True)
    completion_date = fields.Date(tracking=True)
    dlp_end_date = fields.Date(string='DLP End', tracking=True)

    contract_value = fields.Monetary(tracking=True)
    currency_id = fields.Many2one(
        'res.currency', default=lambda s: s.env.company.currency_id)

    # Bonds & insurance
    performance_bond_amount = fields.Monetary()
    performance_bond_expiry = fields.Date(tracking=True)
    advance_bond_amount = fields.Monetary()
    advance_bond_expiry = fields.Date(tracking=True)
    insurance_expiry = fields.Date(tracking=True)

    state = fields.Selection([
        ('draft', 'Draft'),
        ('active', 'Active'),
        ('completed', 'Completed'),
        ('terminated', 'Terminated'),
        ('expired', 'Expired'),
    ], default='draft', tracking=True)

    notes = fields.Html()
    attachment_ids = fields.Many2many('ir.attachment',
                                        string='Contract Documents')

    def action_activate(self):
        self.state = 'active'

    def action_complete(self):
        self.state = 'completed'

    def action_terminate(self):
        self.state = 'terminated'

    def action_expire(self):
        self.state = 'expired'
