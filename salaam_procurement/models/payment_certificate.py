# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError
from datetime import date, timedelta


class PaymentCertificate(models.Model):
    """
    Interim Payment Certificate (IPC).

    Monthly payment workflow:
      Contractor submits valuation → QS certifies → Client approves → Finance pays

    Status: draft → submitted → qs_review → approved → paid

    Retention:
      5% withheld from each certificate until practical completion.
      50% released at practical completion, 50% at DLP end.

    Cumulative tracking:
      Each certificate tracks total certified to date against contract value.
      Prevents over-certification.

    Links to Istisna milestone for automated payment trigger
    and budget line for cost tracking.
    """
    _name = 'salaam.payment.certificate'
    _description = 'Interim Payment Certificate (IPC)'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'project_id, certificate_number desc'

    # ── IDENTITY ──────────────────────────────────────────────────────────────
    name = fields.Char(
        string='IPC Reference', readonly=True, copy=False, default='New',
    )
    certificate_number = fields.Integer(
        string='Certificate #', readonly=True,
        help='Sequential number within the contract',
    )
    state = fields.Selection([
        ('draft',     'Draft'),
        ('submitted', 'Submitted by Contractor'),
        ('qs_review', 'Under QS Review'),
        ('approved',  'Approved — Payment Due'),
        ('paid',      'Paid'),
        ('disputed',  'Disputed'),
    ], string='Status', default='draft', tracking=True)

    # ── LINKS ─────────────────────────────────────────────────────────────────
    project_id = fields.Many2one(
        'salaam.construction.project',
        string='Construction Project', required=True, index=True,
    )
    contractor_id = fields.Many2one(
        'res.partner', string='Contractor', required=True,
    )
    istisna_contract_id = fields.Many2one(
        'dev.contract.istisna',
        string='Istisna Contract',
    )
    milestone_id = fields.Many2one(
        'dev.contract.milestone',
        string='Linked Milestone',
        help='Milestone completed by this payment certificate',
    )
    phase_id = fields.Many2one(
        'salaam.construction.phase',
        string='Construction Phase',
    )
    tender_id = fields.Many2one(
        'salaam.tender',
        string='Original Tender',
    )

    # ── VALUATION PERIOD ──────────────────────────────────────────────────────
    period_start = fields.Date(string='Valuation Period Start', required=True)
    period_end = fields.Date(string='Valuation Period End', required=True)
    submission_date = fields.Date(string='Contractor Submission Date')
    qs_review_date = fields.Date(string='QS Review Date')
    approval_date = fields.Date(string='Approval Date')
    payment_due_date = fields.Date(string='Payment Due Date')
    paid_date = fields.Date(string='Date Paid')

    # ── PERSONNEL ─────────────────────────────────────────────────────────────
    submitted_by = fields.Many2one('res.users', string='Submitted By')
    qs_reviewer_id = fields.Many2one('res.users', string='QS Reviewer')
    approved_by = fields.Many2one('res.users', string='Approved By')
    dispute_reason = fields.Text(string='Dispute Reason')

    # ── FINANCIALS ────────────────────────────────────────────────────────────
    currency_id = fields.Many2one(
        'res.currency', default=lambda self: self.env.company.currency_id,
    )
    contract_value = fields.Monetary(
        string='Contract Value', currency_field='currency_id',
    )
    # Contractor's claimed amount
    gross_valuation_claimed = fields.Monetary(
        string='Gross Valuation (Claimed)',
        currency_field='currency_id',
        help='Total value of work done to date — as claimed by contractor',
    )
    # QS certified amount
    gross_valuation_certified = fields.Monetary(
        string='Gross Valuation (Certified)',
        currency_field='currency_id',
        help='Total value certified by QS after assessment',
    )
    # Retention
    retention_pct = fields.Float(string='Retention (%)', default=5.0)
    retention_held = fields.Monetary(
        string='Retention Held (cumulative)',
        compute='_compute_certificate_amounts',
        store=True, currency_field='currency_id',
    )
    # Previous certificates
    previous_certified_total = fields.Monetary(
        string='Previously Certified (cumulative)',
        currency_field='currency_id',
        help='Sum of all previously approved IPC gross certified amounts',
    )
    # This certificate
    this_certificate_gross = fields.Monetary(
        string='This Certificate — Gross',
        compute='_compute_certificate_amounts',
        store=True, currency_field='currency_id',
    )
    this_certificate_retention = fields.Monetary(
        string='This Certificate — Retention Deducted',
        compute='_compute_certificate_amounts',
        store=True, currency_field='currency_id',
    )
    net_amount_due = fields.Monetary(
        string='Net Amount Due',
        compute='_compute_certificate_amounts',
        store=True, currency_field='currency_id',
    )
    pct_complete = fields.Float(
        string='% Complete',
        compute='_compute_certificate_amounts',
        store=True, digits=(5, 1),
    )
    over_certified = fields.Boolean(
        string='Over-Certification Warning',
        compute='_compute_certificate_amounts',
        store=True,
    )

    notes = fields.Text(string='QS Assessment Notes')

    # ── COMPUTES ──────────────────────────────────────────────────────────────
    @api.depends(
        'gross_valuation_certified', 'previous_certified_total',
        'retention_pct', 'contract_value',
    )
    def _compute_certificate_amounts(self):
        for rec in self:
            certified = rec.gross_valuation_certified or 0
            prev = rec.previous_certified_total or 0
            this_gross = max(0, certified - prev)
            retention = this_gross * (rec.retention_pct / 100)
            net = this_gross - retention
            total_retention = certified * (rec.retention_pct / 100)

            rec.this_certificate_gross = this_gross
            rec.this_certificate_retention = retention
            rec.net_amount_due = net
            rec.retention_held = total_retention
            rec.pct_complete = (
                (certified / rec.contract_value * 100)
                if rec.contract_value else 0
            )
            rec.over_certified = (
                certified > rec.contract_value
                if rec.contract_value else False
            )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'salaam.payment.certificate'
                ) or 'New'
            # Auto certificate number
            if vals.get('project_id') and vals.get('contractor_id'):
                existing_count = self.search_count([
                    ('project_id', '=', vals['project_id']),
                    ('contractor_id', '=', vals['contractor_id']),
                ])
                vals['certificate_number'] = existing_count + 1

        return super().create(vals_list)

    # ── WORKFLOW ──────────────────────────────────────────────────────────────
    def action_submit(self):
        for rec in self:
            rec.state = 'submitted'
            rec.submission_date = date.today()
            rec.submitted_by = self.env.user
            rec.payment_due_date = date.today() + timedelta(days=28)

    def action_qs_review(self):
        self.write({'state': 'qs_review', 'qs_review_date': date.today()})

    def action_approve(self):
        for rec in self:
            if rec.over_certified:
                raise UserError(_(
                    'Certificate would exceed contract value. '
                    'Review gross valuation certified — possible over-certification.'
                ))
            rec.state = 'approved'
            rec.approval_date = date.today()
            rec.approved_by = self.env.user

            # Auto-complete linked milestone
            if rec.milestone_id and rec.milestone_id.state != 'completed':
                rec.milestone_id.state = 'completed'

            rec.message_post(body=_(
                'IPC #%d APPROVED. Net amount due: %s %s. Payment due: %s'
            ) % (rec.certificate_number, rec.net_amount_due,
                 rec.currency_id.symbol, rec.payment_due_date))

    def action_mark_paid(self):
        self.write({'state': 'paid', 'paid_date': date.today()})

    def action_dispute(self):
        self.state = 'disputed'

    def action_reset_draft(self):
        self.state = 'draft'


class ProjectProcurementInherit(models.Model):
    """Adds tender and IPC smart buttons to construction project."""
    _inherit = 'salaam.construction.project'

    tender_ids = fields.One2many('salaam.tender', 'project_id', string='Tenders')
    payment_certificate_ids = fields.One2many(
        'salaam.payment.certificate', 'project_id', string='Payment Certificates',
    )
    tender_count = fields.Integer(compute='_compute_procurement_counts')
    ipc_count = fields.Integer(compute='_compute_procurement_counts')
    pending_ipc_count = fields.Integer(compute='_compute_procurement_counts')
    total_certified = fields.Monetary(
        compute='_compute_procurement_counts',
        string='Total Certified (all contractors)',
        currency_field='currency_id',
    )

    @api.depends(
        'tender_ids', 'payment_certificate_ids',
        'payment_certificate_ids.state',
        'payment_certificate_ids.gross_valuation_certified',
    )
    def _compute_procurement_counts(self):
        for rec in self:
            rec.tender_count = len(rec.tender_ids)
            ipcs = rec.payment_certificate_ids
            rec.ipc_count = len(ipcs)
            rec.pending_ipc_count = len(
                ipcs.filtered(lambda i: i.state in ('submitted', 'qs_review'))
            )
            rec.total_certified = sum(
                ipcs.filtered(lambda i: i.state in ('approved', 'paid'))
                .mapped('this_certificate_gross')
            )

    def action_open_tenders(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Tenders — %s') % self.name,
            'res_model': 'salaam.tender',
            'view_mode': 'list,form',
            'domain': [('project_id', '=', self.id)],
            'context': {'default_project_id': self.id},
        }

    def action_open_ipcs(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Payment Certificates — %s') % self.name,
            'res_model': 'salaam.payment.certificate',
            'view_mode': 'list,form',
            'domain': [('project_id', '=', self.id)],
            'context': {'default_project_id': self.id},
        }
