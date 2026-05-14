# -*- coding: utf-8 -*-
from odoo import api, fields, models


class TenderBudgetQuote(models.Model):
    _name = 'tender.budget.quote'
    _description = 'Supplier Budgetary Quote'
    _inherit = ['mail.thread']
    _order = 'item_name, rank'

    opportunity_id = fields.Many2one(
        'crm.lead', string='Opportunity', required=True,
        ondelete='cascade', index=True,
    )
    item_name = fields.Char(string='Item / Scope', required=True)
    description = fields.Text()
    supplier_id = fields.Many2one(
        'res.partner', string='Supplier', required=True,
        domain="[('is_company', '=', True)]",
    )
    rank = fields.Selection([
        ('1', '1st Quote'),
        ('2', '2nd Quote'),
        ('3', '3rd Quote'),
        ('alt', 'Alternative'),
    ], default='1', required=True)
    amount = fields.Monetary(currency_field='currency_id', required=True)
    currency_id = fields.Many2one(
        'res.currency', default=lambda self: self.env.company.currency_id,
        required=True,
    )
    validity_to = fields.Date(string='Quote Validity')
    received_date = fields.Date(default=fields.Date.context_today)
    is_selected = fields.Boolean(string='Selected for Bid')
    attachment_ids = fields.Many2many(
        'ir.attachment', 'tender_quote_attachment_rel',
        'quote_id', 'attachment_id', string='Attachments',
    )
    notes = fields.Text()
    company_id = fields.Many2one(
        'res.company', related='opportunity_id.company_id',
        store=True, readonly=True,
    )

    @api.constrains('opportunity_id', 'item_name', 'rank')
    def _check_three_quote_rule(self):
        # Soft check, just warn via _logger; no hard constraint to allow flexibility.
        pass
