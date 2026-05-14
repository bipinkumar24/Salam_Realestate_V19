# -*- coding: utf-8 -*-
from odoo import api, fields, models


class TenderBidBond(models.Model):
    _name = 'tender.bid.bond'
    _description = 'Bid Bond / EMD'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'validity_to'

    name = fields.Char(required=True, default='New', copy=False, readonly=True)
    opportunity_id = fields.Many2one(
        'crm.lead', string='Opportunity', required=True,
        ondelete='cascade', index=True, tracking=True,
    )
    bond_type = fields.Selection([
        ('bid', 'Bid Bond'),
        ('emd', 'EMD / Earnest Money Deposit'),
        ('performance', 'Performance Bond'),
        ('advance', 'Advance Payment Guarantee'),
    ], required=True, default='bid', tracking=True)
    required_amount = fields.Monetary(currency_field='currency_id', tracking=True)
    issued_amount = fields.Monetary(currency_field='currency_id', tracking=True)
    currency_id = fields.Many2one(
        'res.currency', default=lambda self: self.env.company.currency_id,
        required=True,
    )
    beneficiary_id = fields.Many2one('res.partner', string='Beneficiary')
    issuer_id = fields.Many2one('res.partner', string='Issuing Bank',
                                domain="[('is_company', '=', True)]")
    reference = fields.Char(string='Bond Reference')
    validity_from = fields.Date(tracking=True)
    validity_to = fields.Date(tracking=True)
    state = fields.Selection([
        ('requested', 'Requested'),
        ('issued', 'Issued'),
        ('submitted', 'Submitted'),
        ('returned', 'Returned'),
        ('forfeited', 'Forfeited'),
        ('expired', 'Expired'),
    ], default='requested', tracking=True)
    attachment_ids = fields.Many2many(
        'ir.attachment', 'tender_bond_attachment_rel',
        'bond_id', 'attachment_id', string='Attachments',
    )
    company_id = fields.Many2one(
        'res.company', related='opportunity_id.company_id',
        store=True, readonly=True,
    )
    notes = fields.Text()

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('tender.bid.bond') or 'BB/0001'
        return super().create(vals_list)

    def action_mark_issued(self):
        self.write({'state': 'issued'})

    def action_mark_submitted(self):
        self.write({'state': 'submitted'})

    def action_mark_returned(self):
        self.write({'state': 'returned'})
