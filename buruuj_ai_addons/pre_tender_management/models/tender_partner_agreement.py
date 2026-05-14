# -*- coding: utf-8 -*-
from odoo import api, fields, models


class TenderPartnerAgreement(models.Model):
    _name = 'tender.partner.agreement'
    _description = 'Bid Partner Agreement'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'validity_to'

    name = fields.Char(required=True, default='New', copy=False, readonly=True)
    opportunity_id = fields.Many2one(
        'crm.lead', string='Opportunity', required=True,
        ondelete='cascade', index=True, tracking=True,
    )
    partner_id = fields.Many2one(
        'res.partner', string='Partner', required=True, tracking=True,
    )
    agreement_type = fields.Selection([
        ('nda', 'NDA / Confidentiality'),
        ('teaming', 'Teaming Agreement'),
        ('jv', 'Joint Venture'),
        ('subcontractor', 'Subcontractor'),
        ('consortium', 'Consortium'),
        ('mou', 'MOU / LOI'),
    ], required=True, default='nda', tracking=True)
    sign_status = fields.Selection([
        ('draft', 'Draft'),
        ('sent', 'Sent for Signature'),
        ('signed', 'Signed'),
        ('expired', 'Expired'),
        ('terminated', 'Terminated'),
    ], default='draft', tracking=True)
    validity_from = fields.Date()
    validity_to = fields.Date()
    scope_of_work = fields.Text()
    revenue_share_pct = fields.Float(string='Revenue Share %')
    attachment_ids = fields.Many2many(
        'ir.attachment', 'tender_agreement_attachment_rel',
        'agreement_id', 'attachment_id', string='Attachments',
    )
    company_id = fields.Many2one(
        'res.company', related='opportunity_id.company_id',
        store=True, readonly=True,
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('tender.partner.agreement') or 'PA/0001'
        return super().create(vals_list)
