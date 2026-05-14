# -*- coding: utf-8 -*-
from odoo import fields, models


class InvestmentLiability(models.Model):
    _name = 'property.investment.liability'
    _description = 'Applicant Liability Line'
    _order = 'sequence, id'

    sequence = fields.Integer(default=10)
    application_id = fields.Many2one(
        'property.investment.application',
        string='Application',
        ondelete='cascade',
        required=True,
    )
    creditor_name = fields.Char(string='Company / Creditor Name', required=True)
    monthly_payment = fields.Monetary(
        string='Monthly Payment',
        currency_field='currency_id',
    )
    months_remaining = fields.Integer(string='Months Remaining')
    outstanding_balance = fields.Monetary(
        string='Outstanding Balance',
        currency_field='currency_id',
    )
    currency_id = fields.Many2one(
        'res.currency',
        related='application_id.currency_id',
        store=True,
    )
    notes = fields.Char(string='Notes')
