# -*- coding: utf-8 -*-
from odoo import fields, models


class TenderAlertSubscription(models.Model):
    _name = 'tender.alert.subscription'
    _description = 'Tender Portal Alert Subscription'
    _inherit = ['mail.thread']
    _order = 'name'

    name = fields.Char(required=True)
    source = fields.Selection([
        ('ted', 'TED (EU)'),
        ('ungm', 'UNGM'),
        ('worldbank', 'World Bank'),
        ('afdb', 'AfDB'),
        ('govt_portal', 'Government Portal'),
        ('email_alias', 'Email Alias'),
        ('rss', 'RSS Feed'),
        ('other', 'Other'),
    ], required=True, default='other')
    endpoint = fields.Char(string='URL / Endpoint / Email')
    keywords = fields.Char(help='Comma-separated keywords used to filter incoming alerts.')
    country_ids = fields.Many2many(
        'res.country', 'tender_alert_country_rel',
        'subscription_id', 'country_id', string='Countries',
    )
    sector_ids = fields.Many2many(
        'res.partner.industry', string='Sectors',
    )
    is_active = fields.Boolean(default=True)
    last_polled = fields.Datetime(readonly=True)
    last_alert_count = fields.Integer(readonly=True)
    notes = fields.Text()


class CrmLead(models.Model):
    _inherit = 'crm.lead'

    alert_subscription_id = fields.Many2one(
        'tender.alert.subscription', string='Alert Source',
        ondelete='set null',
        help='Alert subscription that produced this lead, if any.',
    )
