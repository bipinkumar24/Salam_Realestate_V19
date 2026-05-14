# -*- coding: utf-8 -*-
from datetime import timedelta
from odoo import api, fields, models


class TenderComplianceCertificate(models.Model):
    _name = 'tender.compliance.certificate'
    _description = 'Tender Compliance Certificate'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'valid_to'

    name = fields.Char(string='Certificate Name', required=True, tracking=True)
    certificate_type = fields.Selection([
        ('registration', 'Company Registration'),
        ('tax', 'Tax Compliance'),
        ('iso', 'ISO Certification'),
        ('hse', 'HSE Certification'),
        ('financial', 'Financial Standing'),
        ('insurance', 'Insurance'),
        ('license', 'Trade License'),
        ('other', 'Other'),
    ], string='Type', required=True, default='other', tracking=True)
    issuer = fields.Char(string='Issuing Authority', tracking=True)
    reference_number = fields.Char(string='Reference Number', tracking=True)
    valid_from = fields.Date(string='Valid From', tracking=True)
    valid_to = fields.Date(string='Valid To', required=True, tracking=True)
    alert_lead_time_days = fields.Integer(
        string='Alert Lead Time (Days)', default=30,
        help='Activity scheduled this many days before expiry.',
    )
    attachment_ids = fields.Many2many(
        'ir.attachment', 'tender_certificate_attachment_rel',
        'certificate_id', 'attachment_id', string='Attachments',
    )
    state = fields.Selection([
        ('valid', 'Valid'),
        ('expiring', 'Expiring Soon'),
        ('expired', 'Expired'),
    ], compute='_compute_state', store=True, tracking=True)
    company_id = fields.Many2one(
        'res.company', string='Company',
        default=lambda self: self.env.company, required=True,
    )
    notes = fields.Text(string='Notes')

    @api.depends('valid_to', 'alert_lead_time_days')
    def _compute_state(self):
        today = fields.Date.context_today(self)
        for rec in self:
            if not rec.valid_to:
                rec.state = 'valid'
            elif rec.valid_to < today:
                rec.state = 'expired'
            elif rec.valid_to <= today + timedelta(days=rec.alert_lead_time_days or 0):
                rec.state = 'expiring'
            else:
                rec.state = 'valid'

    @api.model
    def _cron_check_expiring_certificates(self):
        """Schedule activities for certificates approaching expiry."""
        today = fields.Date.context_today(self)
        for cert in self.search([('state', 'in', ('expiring', 'expired'))]):
            cert.activity_schedule(
                'mail.mail_activity_data_warning',
                summary=f'Certificate "{cert.name}" {cert.state}',
                note=f'Valid to: {cert.valid_to}. Renew before submission of any open tender.',
                date_deadline=today,
            )
