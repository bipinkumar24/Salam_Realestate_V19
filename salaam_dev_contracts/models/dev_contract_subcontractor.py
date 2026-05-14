# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class DevContractSubcontractor(models.Model):
    _name = 'dev.contract.subcontractor'
    _description = 'Subcontractor Agreement'
    _inherit = ['dev.contract.base']

    milestone_ids = fields.One2many(
        'dev.contract.milestone', 'contract_id',
        string='Milestones',
        context={'default_res_model': 'dev.contract.subcontractor'},
    )

    contract_type = fields.Selection(default='subcontractor')

    # ── PARTIES ──────────────────────────────────────────────────────────────
    main_contractor_id = fields.Many2one(
        'res.partner', string='Main Contractor', required=True, tracking=True,
    )
    subcontractor_id = fields.Many2one(
        'res.partner', string='Subcontractor', required=True, tracking=True,
    )
    parent_istisna_id = fields.Many2one(
        'dev.contract.istisna', string='Parent Istisna Contract',
        ondelete='restrict', tracking=True,
    )

    # ── SCOPE ─────────────────────────────────────────────────────────────────
    scope_of_works = fields.Html(
        string='Scope of Sub-Works', required=True,
    )
    works_category = fields.Selection(
        selection=[
            ('civil', 'Civil Works'),
            ('mep', 'MEP (Mechanical, Electrical, Plumbing)'),
            ('facade', 'Facade & Cladding'),
            ('fit_out', 'Interior Fit-Out'),
            ('landscaping', 'Landscaping'),
            ('other', 'Other'),
        ],
        string='Works Category', required=True,
    )

    # ── FINANCIAL ─────────────────────────────────────────────────────────────
    subcontract_value = fields.Monetary(
        string='Sub-Contract Value', currency_field='currency_id', required=True,
    )
    retention_rate = fields.Float(
        string='Retention Rate (%)', digits=(5, 2), default=5.0,
    )
    payment_terms_days = fields.Integer(
        string='Payment Terms (days after invoice approval)', default=30,
    )

    # ── SITE & LEGAL ──────────────────────────────────────────────────────────
    site_access_conditions = fields.Text(
        string='Site Access & HSE Requirements',
    )
    variation_order_procedure = fields.Text(
        string='Variation Order Procedure',
        default='All variation orders must be approved in writing by the Main Contractor '
                'Project Manager before works commence. Verbal instructions will not be '
                'recognised for payment purposes.',
    )
    insurance_required = fields.Boolean(
        string='Insurance Required', default=True,
    )
    insurance_value = fields.Monetary(
        string='Minimum Insurance Cover', currency_field='currency_id',
    )

    # ── VALIDATION ────────────────────────────────────────────────────────────
    @api.constrains('subcontract_value', 'parent_istisna_id')
    def _check_value_vs_parent(self):
        for rec in self:
            if rec.parent_istisna_id and rec.subcontract_value:
                if rec.subcontract_value > rec.parent_istisna_id.contract_value:
                    raise ValidationError(_(
                        'Sub-contract value (%s) exceeds the parent Istisna '
                        'contract value (%s). Please verify the amounts.'
                    ) % (rec.subcontract_value, rec.parent_istisna_id.contract_value))

    @api.constrains('date_end', 'parent_istisna_id')
    def _check_dates_vs_parent(self):
        for rec in self:
            if rec.parent_istisna_id and rec.date_end and rec.parent_istisna_id.date_end:
                if rec.date_end > rec.parent_istisna_id.date_end:
                    raise ValidationError(_(
                        'Sub-contract end date (%s) cannot exceed the parent '
                        'Istisna contract end date (%s).'
                    ) % (rec.date_end, rec.parent_istisna_id.date_end))

    def _get_sequence_code(self):
        return 'dev.contract.subcontractor'

    def _check_required_fields(self):
        for rec in self:
            if not rec.subcontractor_id:
                raise ValidationError(_('Subcontractor is required before submitting.'))
            if not rec.scope_of_works:
                raise ValidationError(_('Scope of Works is required before submitting.'))
