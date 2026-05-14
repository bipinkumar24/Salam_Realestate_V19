# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError


class DevContractMusharaka(models.Model):
    _name = 'dev.contract.musharaka'
    _description = 'Diminishing Musharaka Joint Venture Contract'
    _inherit = ['dev.contract.base']

    milestone_ids = fields.One2many(
        'dev.contract.milestone', 'contract_id',
        string='Milestones',
        context={'default_res_model': 'dev.contract.musharaka'},
    )

    contract_type = fields.Selection(default='musharaka')
    sharia_required = fields.Boolean(default=True, readonly=True)

    # ── PARTIES ──────────────────────────────────────────────────────────────
    partner_id = fields.Many2one(
        'res.partner', string='JV Partner', required=True, tracking=True,
    )

    # ── PARTNERSHIP STRUCTURE ─────────────────────────────────────────────────
    total_project_value = fields.Monetary(
        string='Total Project Value', currency_field='currency_id', required=True,
    )
    bank_share_pct = fields.Float(
        string='Bank Initial Share (%)', digits=(5, 2), required=True,
        default=70.0, tracking=True,
    )
    partner_share_pct = fields.Float(
        string='Partner Initial Share (%)', digits=(5, 2),
        compute='_compute_partner_share', store=True,
    )
    bank_contribution = fields.Monetary(
        string='Bank Contribution', compute='_compute_contributions',
        currency_field='currency_id', store=True,
    )
    partner_contribution = fields.Monetary(
        string='Partner Contribution', compute='_compute_contributions',
        currency_field='currency_id', store=True,
    )
    current_bank_share_pct = fields.Float(
        string='Current Bank Share (%)', digits=(5, 2),
        compute='_compute_current_bank_share', store=True,
        help='Real-time bank ownership after redemption tranches are processed',
    )

    # ── PROFIT & LOSS ─────────────────────────────────────────────────────────
    profit_distribution_basis = fields.Selection(
        selection=[
            ('ownership_ratio', 'Ownership Ratio'),
            ('agreed_ratio', 'Agreed Fixed Ratio'),
        ],
        string='Profit Distribution Basis', required=True, default='ownership_ratio',
    )
    agreed_profit_ratio_bank = fields.Float(
        string='Bank Agreed Profit Share (%)', digits=(5, 2),
        help='Only used when Profit Distribution Basis = Agreed Fixed Ratio',
    )

    # ── MANAGEMENT ────────────────────────────────────────────────────────────
    management_party = fields.Selection(
        selection=[
            ('bank', 'Bank'),
            ('partner', 'Partner'),
            ('joint', 'Joint Management'),
        ],
        string='Management Party', required=True, default='joint',
    )
    exit_mechanism = fields.Text(
        string='Exit and Buy-Out Mechanism',
    )

    # ── COMPLIANCE ────────────────────────────────────────────────────────────
    annual_sharia_audit = fields.Boolean(
        string='Annual Sharia Audit Required',
        default=True, readonly=True,
    )
    aaoifi_standard_ref = fields.Char(
        string='AAOIFI Standard Reference',
        default='AAOIFI FAS 4 — Musharaka Financing',
    )

    # ── REDEMPTION SCHEDULE ───────────────────────────────────────────────────
    redemption_ids = fields.One2many(
        'dev.musharaka.redemption', 'musharaka_id',
        string='Redemption Schedule',
    )

    # ── COMPUTED ──────────────────────────────────────────────────────────────
    @api.depends('bank_share_pct')
    def _compute_partner_share(self):
        for rec in self:
            rec.partner_share_pct = 100.0 - (rec.bank_share_pct or 0)

    @api.depends('total_project_value', 'bank_share_pct')
    def _compute_contributions(self):
        for rec in self:
            bank_pct = (rec.bank_share_pct or 0) / 100
            rec.bank_contribution = rec.total_project_value * bank_pct
            rec.partner_contribution = rec.total_project_value * (1 - bank_pct)

    @api.depends('bank_share_pct', 'redemption_ids.tranche_pct', 'redemption_ids.state')
    def _compute_current_bank_share(self):
        for rec in self:
            redeemed = sum(
                r.tranche_pct for r in rec.redemption_ids
                if r.state == 'paid'
            )
            rec.current_bank_share_pct = max(0, (rec.bank_share_pct or 0) - redeemed)

    # ── CONSTRAINTS ───────────────────────────────────────────────────────────
    @api.constrains('bank_share_pct')
    def _check_shares(self):
        for rec in self:
            if not (0 < rec.bank_share_pct < 100):
                raise ValidationError(
                    _('Bank Share must be between 0% and 100% exclusive.')
                )

    @api.constrains('agreed_profit_ratio_bank')
    def _check_profit_ratio(self):
        for rec in self:
            if rec.profit_distribution_basis == 'agreed_ratio':
                if not (0 <= rec.agreed_profit_ratio_bank <= 100):
                    raise ValidationError(
                        _('Agreed Profit Ratio must be between 0% and 100%.')
                    )

    def _get_sequence_code(self):
        return 'dev.contract.musharaka'

    def action_approve(self):
        """All Musharaka require Board approval — enforce the group check."""
        if not self.env.user.has_group('salaam_dev_contracts.group_dev_contracts_admin'):
            raise UserError(_(
                'Diminishing Musharaka contracts require Board / BCC approval. '
                'Please escalate to an authorised approver.'
            ))
        return super().action_approve()

    def _check_required_fields(self):
        for rec in self:
            if not rec.partner_id:
                raise ValidationError(_('JV Partner is required before submitting a Musharaka contract.'))


class DevMushараkaRedemption(models.Model):
    _name = 'dev.musharaka.redemption'
    _description = 'Musharaka Redemption Tranche'
    _order = 'sequence, planned_date'

    musharaka_id = fields.Many2one(
        'dev.contract.musharaka', string='Musharaka Contract',
        required=True, ondelete='cascade',
    )
    sequence = fields.Integer(default=10)
    name = fields.Char(string='Tranche', required=True)
    planned_date = fields.Date(string='Planned Redemption Date', required=True)
    actual_date = fields.Date(string='Actual Date')
    tranche_pct = fields.Float(
        string='Tranche % of Bank Share', digits=(5, 2), required=True,
        help='Percentage of bank ownership to be transferred in this tranche',
    )
    tranche_amount = fields.Monetary(
        string='Tranche Amount', currency_field='currency_id',
        compute='_compute_tranche_amount', store=True,
    )
    currency_id = fields.Many2one(
        'res.currency', related='musharaka_id.currency_id', store=True,
    )
    state = fields.Selection(
        selection=[
            ('pending', 'Pending'),
            ('due', 'Due'),
            ('paid', 'Paid'),
        ],
        string='Status', default='pending',
    )

    @api.depends('musharaka_id.bank_contribution', 'tranche_pct', 'musharaka_id.bank_share_pct')
    def _compute_tranche_amount(self):
        for rec in self:
            if rec.musharaka_id.bank_share_pct:
                rec.tranche_amount = (
                    rec.musharaka_id.bank_contribution *
                    (rec.tranche_pct / rec.musharaka_id.bank_share_pct)
                )
            else:
                rec.tranche_amount = 0
