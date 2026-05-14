# -*- coding: utf-8 -*-
from odoo import models, fields, api


class BuruujTransmittal(models.Model):
    _name = 'buruuj.transmittal'
    _description = 'Document Transmittal'
    _inherit = ['mail.thread']
    _order = 'date desc'

    name = fields.Char(required=True, copy=False, default='New Transmittal')
    project_id = fields.Many2one('project.project', required=True)
    date = fields.Date(default=fields.Date.context_today, required=True)
    sent_to = fields.Many2one('res.partner', string='Sent To', required=True)
    sent_by = fields.Many2one('res.users', default=lambda s: s.env.user)
    purpose = fields.Selection([
        ('information', 'For Information'),
        ('approval', 'For Approval'),
        ('action', 'For Action'),
        ('record', 'For Record'),
    ], default='approval')
    drawing_ids = fields.Many2many('buruuj.drawing', string='Drawings')
    method = fields.Selection([
        ('email', 'Email'),
        ('hand', 'Hand Delivery'),
        ('courier', 'Courier'),
        ('portal', 'Portal Upload'),
    ], default='email')
    notes = fields.Text()
    state = fields.Selection([
        ('draft', 'Draft'),
        ('sent', 'Sent'),
        ('acknowledged', 'Acknowledged'),
    ], default='draft')

    def action_send(self):
        self.state = 'sent'

    def action_acknowledge(self):
        self.state = 'acknowledged'
