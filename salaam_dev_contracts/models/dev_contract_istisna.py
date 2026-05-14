# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError


class DevContractIstisna(models.Model):
    _name = 'dev.contract.istisna'
    _description = 'Istisna Construction Finance Contract'
    _inherit = ['dev.contract.base']

    milestone_ids = fields.One2many(
        'dev.contract.milestone', 'contract_id',
        string='Milestones',
        context={'default_res_model': 'dev.contract.istisna'},
    )

    contract_type = fields.Selection(default='istisna')
    # Istisna is always Sharia — lock it
    sharia_required = fields.Boolean(default=True, readonly=True)

    # ── PARTIES ──────────────────────────────────────────────────────────────
    contractor_id = fields.Many2one(
        'res.partner', string='Main Contractor', required=True, tracking=True,
    )

    # ── CONSTRUCTION SCOPE ────────────────────────────────────────────────────
    construction_spec = fields.Html(
        string='Technical Specification',
        help='Detailed specification including drawings references',
    )
    total_built_area = fields.Float(
        string='Total Built Area (m²)', digits=(10, 2),
    )
    works_category = fields.Selection(
        selection=[
            ('residential', 'Residential'),
            ('commercial', 'Commercial'),
            ('mixed_use', 'Mixed Use'),
            ('infrastructure', 'Infrastructure'),
            ('fit_out', 'Fit-Out Only'),
        ],
        string='Works Category', required=True,
    )

    # ── TIMELINE ──────────────────────────────────────────────────────────────
    construction_start = fields.Date(
        string='Construction Start Date', required=True,
    )
    expected_completion = fields.Date(
        string='Expected Completion Date', required=True,
    )
    handover_date_actual = fields.Date(string='Actual Handover Date')

    # ── FINANCIAL TERMS ───────────────────────────────────────────────────────
    payment_basis = fields.Selection(
        selection=[
            ('milestone', 'Milestone-Based'),
            ('pct_complete', 'Percentage Complete'),
            ('fixed_schedule', 'Fixed Schedule'),
        ],
        string='Payment Basis', required=True, default='milestone',
    )
    retention_rate = fields.Float(
        string='Retention Rate (%)', digits=(5, 2), default=5.0,
        help='Percentage withheld from each milestone payment until completion',
    )
    delay_penalty_rate = fields.Float(
        string='Delay Penalty Rate (% per day)',
        digits=(5, 4),
        help='Sharia-permissible: penalty structured as compensation for actual loss, not punitive interest',
    )
    defect_liability_months = fields.Integer(
        string='Defect Liability Period (months)', default=12,
    )

    # ── SHARIA / COMPLIANCE ───────────────────────────────────────────────────
    aaoifi_standard_ref = fields.Char(
        string='AAOIFI Standard Reference',
        default='AAOIFI FAS 10 — Istisna and Parallel Istisna',
    )

    # ── SUBCONTRACTS ──────────────────────────────────────────────────────────
    subcontract_ids = fields.One2many(
        'dev.contract.subcontractor', 'parent_istisna_id',
        string='Sub-Contracts',
    )
    subcontract_count = fields.Integer(
        compute='_compute_subcontract_count', string='Sub-Contracts',
    )

    @api.depends('subcontract_ids')
    def _compute_subcontract_count(self):
        for rec in self:
            rec.subcontract_count = len(rec.subcontract_ids)

    def action_open_subcontracts(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Sub-Contracts — %s') % self.name,
            'res_model': 'dev.contract.subcontractor',
            'view_mode': 'list,form',
            'domain': [('parent_istisna_id', '=', self.id)],
            'context': {'default_parent_istisna_id': self.id},
        }

    def _get_sequence_code(self):
        return 'dev.contract.istisna'

    def action_complete(self):
        if not self.handover_date_actual:
            self.handover_date_actual = fields.Date.today()
        return super().action_complete()

    def _check_required_fields(self):
        for rec in self:
            if not rec.contractor_id:
                raise ValidationError(_('Main Contractor is required before submitting an Istisna contract.'))
            if not rec.construction_start or not rec.expected_completion:
                raise ValidationError(_('Construction Start and Expected Completion dates are required.'))
