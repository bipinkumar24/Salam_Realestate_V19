# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError
from datetime import date, timedelta


# ── MODEL 3: EOT CLAIM ────────────────────────────────────────────────────────

class EOTClaim(models.Model):
    """
    Extension of Time (EOT) Claim.

    When a contractor claims additional time due to events
    outside their control or caused by the Employer/PM.

    Relevant for Salaam City, Djibouti:
      - Red Sea disruption → material delivery delays
      - Extreme heat (Djibouti climate) → adverse weather
      - Port delays → late material delivery
      - Late SI from PM → employer-caused delay
      - Utility strike coordination failures

    The grant of EOT:
      - Extends the contract completion date
      - Prevents the contractor being liable for delay damages (LDs)
      - Does NOT automatically entitle the contractor to additional money
        (prolongation cost is a separate claim)

    Status flow:
      submitted → under_assessment → granted / rejected / partial

    Running EOT total:
      Each granted EOT adds to eot_total_granted on the linked programme.
      The revised contract completion date is recomputed automatically.
    """
    _name = 'salaam.eot.claim'
    _description = 'Extension of Time Claim'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'project_id, name desc'

    # ── IDENTITY ──────────────────────────────────────────────────────────────
    name = fields.Char(
        string='EOT Reference', readonly=True, copy=False, default='New',
    )
    state = fields.Selection([
        ('submitted',        'Submitted'),
        ('under_assessment', 'Under Assessment'),
        ('granted',          'Granted'),
        ('partial',          'Partially Granted'),
        ('rejected',         'Rejected'),
    ], string='Status', default='submitted', track_visibility='onchange')

    # ── CLASSIFICATION ────────────────────────────────────────────────────────
    delay_event = fields.Selection([
        ('employer_delay',     'Employer / PM Caused Delay'),
        ('late_instruction',   'Late Engineer\'s Instruction'),
        ('late_drawing',       'Late Issue of Drawing'),
        ('variation',          'Instructed Variation'),
        ('force_majeure',      'Force Majeure'),
        ('adverse_weather',    'Adverse Weather Conditions'),
        ('material_delivery',  'Late Material Delivery (Supply Chain)'),
        ('utility_strike',     'Utility / Infrastructure Failure'),
        ('port_delay',         'Port / Customs Delay (Djibouti)'),
        ('red_sea_disruption', 'Red Sea Shipping Disruption'),
        ('statutory_change',   'Statutory / Regulatory Change'),
        ('unforeseen_ground',  'Unforeseen Ground Conditions'),
        ('other',              'Other'),
    ], string='Delay Event Type', required=True)

    entitlement_basis = fields.Selection([
        ('employer_risk',  'Employer Risk Event — EOT + Cost'),
        ('neutral_event',  'Neutral Risk Event — EOT Only (no cost)'),
        ('disputed',       'Disputed Entitlement'),
    ], string='Entitlement Basis', default='employer_risk', track_visibility='onchange')

    # ── LINKS ─────────────────────────────────────────────────────────────────
    project_id = fields.Many2one(
        'salaam.construction.project', required=True, index=True,
    )
    # contractor_party_id = fields.Many2one(
    #     'salaam.project.party',
    #     string='Claiming Contractor',
    # )
    contractor_party_id = fields.Many2one(
        'res.partner',
        string='Submitted By (Contractor)',
    )
    contractor_id = fields.Many2one('res.partner', string='Contractor', compute='_compute_contractor_id', store=True,)
    site_instruction_id = fields.Many2one(
        'salaam.site.instruction',
        string='Causative Site Instruction',
        help='The SI that caused the delay event (if applicable)',
    )
    programme_id = fields.Many2one(
        'salaam.contractor.programme',
        string='Affected Programme',
    )
    assessor_id = fields.Many2one('res.users', string='PM / QS Assessor')

    # ── DATES ─────────────────────────────────────────────────────────────────
    delay_event_start = fields.Date(string='Delay Event Start Date', required=True)
    delay_event_end = fields.Date(string='Delay Event End Date')
    submission_date = fields.Date(
        string='Claim Submission Date', default=fields.Date.today,
    )
    assessment_date = fields.Date(string='Assessment Completion Date')
    decision_date = fields.Date(string='Decision Date')

    # ── NOTICE REQUIREMENTS ───────────────────────────────────────────────────
    notice_given = fields.Boolean(
        string='Contractual Notice Given',
        help='Has the contractor given timely notice per contract conditions?',
        default=False,
    )
    notice_date = fields.Date(string='Notice Date')
    notice_within_contract = fields.Boolean(
        string='Notice Within Contract Period',
        compute='_compute_notice_compliance', store=True,
    )

    # ── CLAIM QUANTUM ─────────────────────────────────────────────────────────
    days_claimed = fields.Integer(
        string='Calendar Days Claimed', required=True,
    )
    days_granted = fields.Integer(
        string='Calendar Days Granted', default=0,
    )
    days_rejected = fields.Integer(
        string='Calendar Days Rejected',
        compute='_compute_days_rejected', store=True,
    )

    # ── ORIGINAL & REVISED DATES ──────────────────────────────────────────────
    original_completion_date = fields.Date(
        string='Original Contract Completion Date',
    )
    revised_completion_date = fields.Date(
        string='Revised Completion Date (after EOT)',
        compute='_compute_revised_completion', store=True,
    )

    # ── PROLONGATION COST ─────────────────────────────────────────────────────
    has_prolongation_cost = fields.Boolean(
        string='Prolongation Cost Claimed?', default=False,
    )
    currency_id = fields.Many2one(
        'res.currency', default=lambda self: self.env.company.currency_id,
    )
    prolongation_cost_claimed = fields.Monetary(
        string='Prolongation Cost Claimed',
        currency_field='currency_id',
    )
    prolongation_cost_agreed = fields.Monetary(
        string='Prolongation Cost Agreed',
        currency_field='currency_id',
    )

    # ── NARRATIVE ─────────────────────────────────────────────────────────────
    contractor_narrative = fields.Text(
        string='Contractor\'s Delay Narrative',
    )
    pm_assessment_notes = fields.Text(
        string='PM / QS Assessment Notes',
    )
    rejection_reason = fields.Text(string='Rejection Reason')

    # ── COMPUTES ──────────────────────────────────────────────────────────────

    @api.depends('contractor_party_id')
    def _compute_contractor_id(self):
        for rec in self:
            try:
                rec.contractor_id = rec.contractor_party_id.partner_id if rec.contractor_party_id else False
            except Exception:
                rec.contractor_id = False

    @api.depends('notice_date', 'delay_event_start')
    def _compute_notice_compliance(self):
        """Most contracts require notice within 28 days of delay event."""
        for rec in self:
            if rec.notice_date and rec.delay_event_start:
                delta = (rec.notice_date - rec.delay_event_start).days
                rec.notice_within_contract = delta <= 28
            else:
                rec.notice_within_contract = False

    @api.depends('days_claimed', 'days_granted')
    def _compute_days_rejected(self):
        for rec in self:
            rec.days_rejected = max(0, rec.days_claimed - rec.days_granted)

    @api.depends('original_completion_date', 'days_granted', 'state')
    def _compute_revised_completion(self):
        for rec in self:
            if rec.original_completion_date and rec.days_granted and rec.state in ('granted', 'partial'):
                rec.revised_completion_date = (
                    rec.original_completion_date + timedelta(days=rec.days_granted)
                )
            else:
                rec.revised_completion_date = False

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'salaam.eot.claim'
                ) or 'New'
        return super().create(vals_list)

    # ── WORKFLOW ──────────────────────────────────────────────────────────────
    def action_assess(self):
        self.write({'state': 'under_assessment', 'assessment_date': date.today()})

    def action_grant(self):
        for rec in self:
            if not rec.days_granted:
                raise UserError(_('Enter the number of days granted before confirming.'))
            rec.state = 'granted'
            rec.decision_date = date.today()
            # Update programme if linked
            if rec.programme_id:
                rec.programme_id.eot_total_granted += rec.days_granted
            rec.message_post(body=_(
                'EOT GRANTED: %d days. Revised completion: %s. Prolongation cost agreed: %s %s'
            ) % (rec.days_granted, rec.revised_completion_date,
                 rec.prolongation_cost_agreed, rec.currency_id.symbol))

    def action_partial(self):
        for rec in self:
            if not rec.days_granted:
                raise UserError(_('Enter the days granted (partial) before confirming.'))
            rec.state = 'partial'
            rec.decision_date = date.today()
            if rec.programme_id:
                rec.programme_id.eot_total_granted += rec.days_granted

    def action_reject(self):
        for rec in self:
            rec.state = 'rejected'
            rec.days_granted = 0
            rec.decision_date = date.today()
            rec.message_post(body=_(
                'EOT REJECTED. %d days claimed, 0 days granted. Reason: %s'
            ) % (rec.days_claimed, rec.rejection_reason or '—'))


# ── MODEL 4: CONTRACTOR PROGRAMME ─────────────────────────────────────────────

class ContractorProgramme(models.Model):
    """
    Contractor Programme submission and approval register.

    The contractor is obligated to submit a detailed works programme
    at contract award and update it monthly (or as instructed).

    Programme types:
      baseline   — initial programme at contract award (approved = contract baseline)
      revised    — monthly update or event-driven revision
      recovery   — submitted when contractor is in delay (PM may instruct)
      as_built   — final record of actual dates (produced at completion)

    The approved baseline programme is the reference against which
    delays are measured for EOT claims.

    Float:
      Total float (project float) and free float are recorded.
      Contractor's ownership of float is a contract matter —
      captured in float_ownership field.

    Status flow:
      draft → submitted → under_review → approved / rejected
      Rejected programmes → contractor revises → resubmits (new revision)
    """
    _name = 'salaam.contractor.programme'
    _description = 'Contractor Programme'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'project_id, submission_date desc'

    # ── IDENTITY ──────────────────────────────────────────────────────────────
    name = fields.Char(
        string='Programme Reference', readonly=True, copy=False, default='New',
    )
    revision = fields.Char(
        string='Revision', default='A',
        help='A, B, C... for sequential revisions of the same type',
    )
    state = fields.Selection([
        ('draft',       'Draft'),
        ('submitted',   'Submitted for Approval'),
        ('under_review','Under Review'),
        ('approved',    'Approved'),
        ('rejected',    'Rejected — Revise & Resubmit'),
        ('superseded',  'Superseded'),
    ], string='Status', default='draft', track_visibility='onchange')

    # ── CLASSIFICATION ────────────────────────────────────────────────────────
    programme_type = fields.Selection([
        ('baseline', 'Baseline Programme (Contract Award)'),
        ('revised',  'Revised Programme (Monthly Update)'),
        ('recovery', 'Recovery Programme (Delay Mitigation)'),
        ('as_built', 'As-Built Programme (Completion Record)'),
    ], string='Programme Type', required=True, default='baseline')

    is_baseline = fields.Boolean(
        string='Is Approved Baseline',
        default=False,
        help='True only for the programme that forms the contract baseline for delay measurement',
    )

    # ── LINKS ─────────────────────────────────────────────────────────────────
    project_id = fields.Many2one(
        'salaam.construction.project', required=True, index=True,
    )
    # contractor_party_id = fields.Many2one(
    #     'salaam.project.party',
    #     string='Submitted By (Contractor)',
    # )
    contractor_party_id = fields.Many2one(
        'res.partner',
        string='Submitted By (Contractor)',
    )
    contractor_id = fields.Many2one('res.partner', string='Contractor', compute='_compute_contractor_id', store=True,)
    reviewer_id = fields.Many2one('res.users', string='PM Reviewer')
    approved_by = fields.Many2one('res.users', string='Approved By')
    superseded_by_id = fields.Many2one(
        'salaam.contractor.programme',
        string='Superseded By',
        readonly=True,
    )

    # ── KEY DATES ─────────────────────────────────────────────────────────────
    submission_date = fields.Date(
        string='Submission Date', default=fields.Date.today,
    )
    review_deadline = fields.Date(
        string='Review Deadline',
        help='PM must respond within 14 days of submission (typical contract requirement)',
    )
    approval_date = fields.Date(string='Approval Date')
    rejection_date = fields.Date(string='Rejection Date')

    # ── PROGRAMME DATES ───────────────────────────────────────────────────────
    programme_start = fields.Date(
        string='Programme Start Date', required=True,
    )
    programme_completion = fields.Date(
        string='Programme Completion Date (as submitted)', required=True,
    )
    contract_completion_date = fields.Date(
        string='Contract Completion Date',
        help='The contractual completion date — may differ from programme completion if contractor has float',
    )
    programme_duration_days = fields.Integer(
        string='Programme Duration (days)',
        compute='_compute_duration', store=True,
    )

    # ── EOT TRACKING ──────────────────────────────────────────────────────────
    eot_total_granted = fields.Integer(
        string='Total EOT Granted (days)',
        default=0,
        help='Cumulative days granted across all EOT claims. Updated automatically when EOTs are granted.',
    )
    revised_contract_completion = fields.Date(
        string='Revised Contract Completion (with EOT)',
        compute='_compute_revised_completion', store=True,
    )
    delay_to_completion = fields.Integer(
        string='Current Delay to Completion (days)',
        compute='_compute_delay', store=True,
    )
    is_in_delay = fields.Boolean(
        string='Programme in Delay',
        compute='_compute_delay', store=True,
    )

    # ── FLOAT ─────────────────────────────────────────────────────────────────
    total_float_days = fields.Integer(string='Total Float (days)', default=0)
    critical_path_flagged = fields.Boolean(
        string='Critical Path Issues Flagged', default=False,
    )
    float_ownership = fields.Selection([
        ('employer', 'Employer Owns Float'),
        ('contractor', 'Contractor Owns Float'),
        ('shared', 'Shared Float'),
        ('contract', 'Per Contract Terms'),
    ], string='Float Ownership', default='contract')

    # ── NARRATIVE ─────────────────────────────────────────────────────────────
    programme_narrative = fields.Text(
        string='Programme Narrative / Key Assumptions',
    )
    review_comments = fields.Text(string='PM Review Comments')
    rejection_reason = fields.Text(string='Rejection Reason')

    # ── PHASE MAPPING ─────────────────────────────────────────────────────────
    phase_mapping_ids = fields.One2many(
        'salaam.programme.phase.mapping',
        'programme_id',
        string='Phase Mappings',
        help='Maps this programme\'s activities to platform construction phases',
    )

    # ── COMPUTES ──────────────────────────────────────────────────────────────
    @api.depends('programme_start', 'programme_completion')
    def _compute_duration(self):
        for rec in self:
            if rec.programme_start and rec.programme_completion:
                rec.programme_duration_days = (
                    rec.programme_completion - rec.programme_start
                ).days
            else:
                rec.programme_duration_days = 0

    @api.depends('contract_completion_date', 'eot_total_granted')
    def _compute_revised_completion(self):
        for rec in self:
            if rec.contract_completion_date and rec.eot_total_granted:
                rec.revised_contract_completion = (
                    rec.contract_completion_date +
                    timedelta(days=rec.eot_total_granted)
                )
            else:
                rec.revised_contract_completion = rec.contract_completion_date

    @api.depends('programme_completion', 'revised_contract_completion')
    def _compute_delay(self):
        today = date.today()
        for rec in self:
            effective_completion = rec.revised_contract_completion or rec.contract_completion_date
            if effective_completion and rec.programme_completion:
                delta = (rec.programme_completion - effective_completion).days
                rec.delay_to_completion = max(0, delta)
                rec.is_in_delay = rec.programme_completion > effective_completion
            else:
                rec.delay_to_completion = 0
                rec.is_in_delay = False

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'salaam.contractor.programme'
                ) or 'New'
        return super().create(vals_list)

    # ── WORKFLOW ──────────────────────────────────────────────────────────────
    def action_submit(self):
        for rec in self:
            rec.state = 'submitted'
            if rec.submission_date:
                rec.review_deadline = rec.submission_date + timedelta(days=14)
            rec.message_post(body=_(
                'Programme %s Rev %s submitted. Type: %s. '
                'Programme completion: %s. Review deadline: %s.'
            ) % (rec.name, rec.revision, rec.programme_type,
                 rec.programme_completion, rec.review_deadline))

    def action_review(self):
        self.state = 'under_review'

    def action_approve(self):
        for rec in self:
            rec.state = 'approved'
            rec.approval_date = date.today()
            rec.approved_by = self.env.user

            # If baseline, set is_baseline and supersede any previous baseline
            if rec.programme_type == 'baseline' and not rec.is_baseline:
                rec.is_baseline = True
                old_baselines = self.search([
                    ('project_id', '=', rec.project_id.id),
                    ('is_baseline', '=', True),
                    ('id', '!=', rec.id),
                ])
                old_baselines.write({
                    'is_baseline': False,
                    'state': 'superseded',
                    'superseded_by_id': rec.id,
                })

            rec.message_post(body=_(
                'Programme APPROVED. Rev %s. Completion: %s. '
                '%s%s'
            ) % (rec.revision, rec.programme_completion,
                 'SET AS BASELINE. ' if rec.is_baseline else '',
                 f'EOT total: {rec.eot_total_granted} days.' if rec.eot_total_granted else ''))

    def action_reject(self):
        for rec in self:
            rec.state = 'rejected'
            rec.rejection_date = date.today()
            rec.message_post(body=_(
                'Programme rejected. Reason: %s'
            ) % (rec.rejection_reason or '—'))

    def action_reset_draft(self):
        self.state = 'draft'


class ProgrammePhasMapping(models.Model):
    """Maps a programme submission to platform construction phases."""
    _name = 'salaam.programme.phase.mapping'
    _description = 'Programme Phase Mapping'
    _order = 'programme_id, sequence'

    programme_id = fields.Many2one(
        'salaam.contractor.programme', ondelete='cascade', required=True,
    )
    sequence = fields.Integer(default=10)
    phase_id = fields.Many2one(
        'salaam.construction.phase',
        string='Construction Phase',
        required=True,
    )
    programme_activity_name = fields.Char(
        string='Programme Activity Name',
        help='As labelled in the contractor\'s programme document',
    )
    planned_start = fields.Date(string='Programme Planned Start')
    planned_finish = fields.Date(string='Programme Planned Finish')
    actual_start = fields.Date(string='Actual Start')
    actual_finish = fields.Date(string='Actual Finish')
    float_days = fields.Integer(string='Float (days)', default=0)
    on_critical_path = fields.Boolean(string='On Critical Path', default=False)
    notes = fields.Char(string='Notes')
