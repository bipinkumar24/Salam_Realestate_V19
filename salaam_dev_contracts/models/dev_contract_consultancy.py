# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class DevContractConsultancy(models.Model):
    _name = 'dev.contract.consultancy'
    _description = 'Consultancy Agreement'
    _inherit = ['dev.contract.base']

    milestone_ids = fields.One2many(
        'dev.contract.milestone', 'contract_id',
        string='Milestones',
        context={'default_res_model': 'dev.contract.consultancy'},
    )

    contract_type = fields.Selection(default='consultancy')

    # ── PARTIES ──────────────────────────────────────────────────────────────
    client_id = fields.Many2one(
        'res.partner', string='Client',
        default=lambda self: self.env.company.partner_id,
        required=True,
    )
    consultant_id = fields.Many2one(
        'res.partner', string='Consultant', required=True, tracking=True,
    )

    # ── SERVICE SCOPE ─────────────────────────────────────────────────────────
    service_scope = fields.Html(
        string='Scope of Services', required=True,
    )
    service_category = fields.Selection(
        selection=[
            ('engineering', 'Engineering'),
            ('legal', 'Legal'),
            ('financial', 'Financial Advisory'),
            ('planning', 'Urban / Master Planning'),
            ('technical', 'Technical Inspection'),
            ('other', 'Other'),
        ],
        string='Service Category', required=True,
    )
    deliverables = fields.Html(string='Deliverables and Acceptance Criteria')

    # ── FEE STRUCTURE ─────────────────────────────────────────────────────────
    fee_structure = fields.Selection(
        selection=[
            ('lump_sum', 'Lump Sum'),
            ('time_materials', 'Time and Materials'),
            ('retainer', 'Monthly Retainer'),
            ('success_fee', 'Success Fee'),
        ],
        string='Fee Structure', required=True, default='lump_sum',
    )
    fee_amount = fields.Monetary(
        string='Lump Sum Fee', currency_field='currency_id',
        help='Used when Fee Structure = Lump Sum',
    )
    hourly_rate = fields.Monetary(
        string='Hourly Rate', currency_field='currency_id',
        help='Used when Fee Structure = Time and Materials',
    )
    monthly_retainer = fields.Monetary(
        string='Monthly Retainer', currency_field='currency_id',
        help='Used when Fee Structure = Monthly Retainer',
    )

    # ── LEGAL TERMS ───────────────────────────────────────────────────────────
    confidentiality_clause = fields.Boolean(
        string='Confidentiality / NDA Included', default=True,
    )
    ip_ownership = fields.Selection(
        selection=[
            ('client', 'Client'),
            ('consultant', 'Consultant'),
            ('joint', 'Joint'),
        ],
        string='IP Ownership of Deliverables', required=True, default='client',
    )
    professional_indemnity_value = fields.Monetary(
        string='PI Insurance Cover Required', currency_field='currency_id',
    )
    termination_notice_days = fields.Integer(
        string='Termination Notice (days)', default=30,
    )
    governing_law = fields.Char(
        string='Governing Law', default='Republic of Djibouti',
    )

    def _get_sequence_code(self):
        return 'dev.contract.consultancy'

    def action_submit(self):
        for rec in self:
            if not rec.confidentiality_clause:
                rec.message_post(
                    body=_(
                        'Warning: This consultancy agreement is being submitted '
                        'without a Confidentiality / NDA clause. '
                        'Please confirm this is intentional before proceeding.'
                    )
                )
        return super().action_submit()

    def _check_required_fields(self):
        for rec in self:
            if not rec.consultant_id:
                raise ValidationError(_('Consultant is required before submitting.'))
            if not rec.service_scope:
                raise ValidationError(_('Scope of Services is required before submitting.'))
