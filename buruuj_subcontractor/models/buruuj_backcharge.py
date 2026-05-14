# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class BuruujBackcharge(models.Model):
    """Recoveries from subcontractor — site services, materials, rework."""
    _name = 'buruuj.backcharge'
    _description = 'Subcontractor Back-charge'
    _order = 'date desc'

    name = fields.Char(required=True, default='Back-charge')
    subcontract_id = fields.Many2one('buruuj.subcontract', required=True)
    project_id = fields.Many2one(
        related='subcontract_id.project_id', store=True)
    partner_id = fields.Many2one(
        related='subcontract_id.partner_id', store=True)
    date = fields.Date(default=fields.Date.context_today)
    category = fields.Selection([
        ('material', 'Material Issued'),
        ('rework', 'Rework / Defects'),
        ('site_service', 'Site Services'),
        ('safety', 'Safety Violation Penalty'),
        ('ld', 'Liquidated Damages'),
        ('other', 'Other'),
    ], default='material', required=True)
    description = fields.Text()
    amount = fields.Monetary(required=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('applied', 'Applied to IPC'),
        ('disputed', 'Disputed'),
    ], default='draft')
    currency_id = fields.Many2one(
        related='subcontract_id.currency_id', store=True)

    def action_confirm(self):
        self.state = 'confirmed'

    def action_apply(self):
        self.state = 'applied'

    def action_dispute(self):
        self.state = 'disputed'
