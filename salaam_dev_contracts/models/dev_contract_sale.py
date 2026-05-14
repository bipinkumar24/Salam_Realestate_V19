# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class DevContractSale(models.Model):
    _name = 'dev.contract.sale'
    _description = 'Sale Contract'
    _inherit = ['dev.contract.base']

    milestone_ids = fields.One2many(
        'dev.contract.milestone', 'contract_id',
        string='Milestones',
        context={'default_res_model': 'dev.contract.sale'},
    )

    contract_type = fields.Selection(default='sale')

    # ── PARTIES ──────────────────────────────────────────────────────────────
    buyer_id = fields.Many2one(
        'res.partner', string='Buyer', required=True, tracking=True,
    )
    seller_id = fields.Many2one(
        'res.partner', string='Seller',
        default=lambda self: self.env.company.partner_id,
        required=True, tracking=True,
    )

    # ── FINANCIAL ─────────────────────────────────────────────────────────────
    purchase_price = fields.Monetary(
        string='Purchase Price', currency_field='currency_id', required=True,
    )
    down_payment = fields.Monetary(
        string='Down Payment', currency_field='currency_id',
    )
    down_payment_date = fields.Date(string='Down Payment Due Date')
    balance_due = fields.Monetary(
        string='Balance Due', compute='_compute_balance_due',
        currency_field='currency_id', store=True,
    )

    # ── PROPERTY DETAILS ──────────────────────────────────────────────────────
    transfer_date = fields.Date(string='Planned Title Transfer Date')
    title_file_no = fields.Char(
        string='Title File Number',
        compute='_compute_title_file_no', store=True,
    )
    property_condition = fields.Text(string='Property Condition at Sale')
    warranty_period = fields.Integer(
        string='Warranty Period (months)', default=12,
    )

    # ── LEGAL ─────────────────────────────────────────────────────────────────
    penalty_rate = fields.Float(
        string='Late Payment Charity Rate (% p.a.)',
        help='Sharia-compliant: proceeds go to charity, not retained by bank',
        digits=(5, 4),
    )
    governing_law = fields.Char(
        string='Governing Law', default='Republic of Djibouti',
    )

    # ── COMPUTED ──────────────────────────────────────────────────────────────
    @api.depends('purchase_price', 'down_payment')
    def _compute_balance_due(self):
        for rec in self:
            rec.balance_due = (rec.purchase_price or 0) - (rec.down_payment or 0)

    @api.depends('property_id')
    def _compute_title_file_no(self):
        for rec in self:
            rec.title_file_no = (
                    getattr(rec.property_id, 'tf_no', False) or
                    getattr(rec.property_id, 'title_number', False) or
                    getattr(rec.property_id, 'title_no', False) or
                    ''
            ) if rec.property_id else ''

    def _get_sequence_code(self):
        return 'dev.contract.sale'

    def _check_required_fields(self):
        for rec in self:
            if not rec.buyer_id:
                raise ValidationError(_('A Buyer must be specified before submitting.'))
