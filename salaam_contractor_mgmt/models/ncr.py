# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError
from datetime import date, timedelta


class NCR(models.Model):
    """
    Non-Conformance Report (NCR).

    Raised when the contractor's work does not conform to:
      - Contract specification
      - Approved drawings
      - Approved material submittals
      - Applicable codes and standards (AAOIFI, local building code)

    DISTINCT FROM SNAGGING:
      - NCRs happen DURING construction (quality control)
      - Snagging happens AT COMPLETION (pre-handover inspection)
      - An unresolved NCR can become a snag item if not closed before
        practical completion — tracked via snag_list_id link

    Severity:
      critical    — structural/safety risk, STOP WORK on affected area
      major       — significant non-conformance, work cannot proceed
      minor       — non-conformance, can continue with corrective action
      observation — advisory, no formal corrective action required

    Corrective Action Plan (CAP):
      Contractor must submit a CAP within the response deadline.
      CAP is reviewed and approved/rejected by QA Engineer.
      Once approved, contractor executes rectification.
      NCR closed only when QA verifies conformance restored.

    Status flow:
      open → cap_submitted → cap_approved → rectifying → verified_closed
                          → cap_rejected (→ cap_submitted again)
                                                       → rejected_permanent
    """
    _name = 'salaam.ncr'
    _description = 'Non-Conformance Report'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'project_id, name desc'

    # ── IDENTITY ──────────────────────────────────────────────────────────────
    name = fields.Char(
        string='NCR Reference', readonly=True, copy=False, default='New',
    )
    title = fields.Char(string='NCR Title', required=True)
    state = fields.Selection([
        ('open',             'Open'),
        ('cap_submitted',    'CAP Submitted'),
        ('cap_approved',     'CAP Approved — Rectifying'),
        ('cap_rejected',     'CAP Rejected — Resubmit'),
        ('rectifying',       'Rectification In Progress'),
        ('verification',     'Awaiting QA Verification'),
        ('closed',           'Closed — Conformance Restored'),
        ('rejected_permanent','Permanently Rejected'),
    ], string='Status', default='open', track_visibility='onchange')

    # ── CLASSIFICATION ────────────────────────────────────────────────────────
    severity = fields.Selection([
        ('critical',    'Critical — Stop Work'),
        ('major',       'Major — Cannot Proceed'),
        ('minor',       'Minor — Continue with CAP'),
        ('observation', 'Observation — Advisory'),
    ], string='Severity', required=True, default='minor', track_visibility='onchange')

    ncr_category = fields.Selection([
        ('structural',      'Structural / Civil'),
        ('mep',             'MEP'),
        ('material',        'Material Non-Conformance'),
        ('workmanship',     'Workmanship'),
        ('dimensional',     'Dimensional / Setting Out'),
        ('documentation',   'Documentation / Submittal'),
        ('environmental',   'Environmental'),
        ('hse',             'HSE Violation'),
        ('other',           'Other'),
    ], string='NCR Category', required=True)

    work_stopped = fields.Boolean(
        string='Work Stopped in Affected Area',
        default=False,
        help='Set True for Critical NCRs — work must stop until CAP approved',
    )

    # ── LINKS ─────────────────────────────────────────────────────────────────
    project_id = fields.Many2one(
        'salaam.construction.project', required=True, index=True,
    )
    phase_id = fields.Many2one(
        'salaam.construction.phase',
    )
    # contractor_party_id = fields.Many2one(
    #     'salaam.project.party',
    #     string='Responsible Contractor',
    # )
    contractor_party_id = fields.Many2one(
        'res.partner',
        string='Responsible Contractor',
    )
    contractor_id = fields.Many2one('res.partner', string='Contractor', compute='_compute_contractor_id', store=True,)
    raised_by = fields.Many2one(
        'res.users', string='Raised By',
        default=lambda self: self.env.user,
    )
    qa_reviewer_id = fields.Many2one('res.users', string='QA Reviewer')
    drawing_ref = fields.Char(string='Related Drawing Reference')
    spec_clause = fields.Char(string='Contract Spec Clause Reference')

    # ── SI LINK ────────────────────────────────────────────────────────────────
    site_instruction_id = fields.Many2one(
        'salaam.site.instruction',
        string='Related Site Instruction',
        help='SI issued to formally instruct the remedy',
    )

    # ── SNAG LINK ─────────────────────────────────────────────────────────────
    snag_list_id = fields.Many2one(
        'salaam.snag.list',
        string='Carried to Snag List',
        help='Set if this NCR was not closed before practical completion and carried to the snag inspection',
    )

    # ── DATES ─────────────────────────────────────────────────────────────────
    raised_date = fields.Date(
        string='Date Raised', required=True, default=fields.Date.today,
    )
    cap_response_deadline = fields.Date(
        string='CAP Response Deadline',
        compute='_compute_cap_deadline', store=True,
    )
    cap_submitted_date = fields.Date(string='CAP Submitted Date')
    cap_approved_date = fields.Date(string='CAP Approved Date')
    rectification_deadline = fields.Date(string='Rectification Deadline')
    verification_date = fields.Date(string='Verification Date')
    closed_date = fields.Date(string='Date Closed')
    days_open = fields.Integer(
        string='Days Open', compute='_compute_days_open', store=True,
    )

    # ── NCR DESCRIPTION ───────────────────────────────────────────────────────
    location_description = fields.Char(string='Location on Site')
    non_conformance_description = fields.Text(
        string='Description of Non-Conformance', required=True,
    )
    specification_requirement = fields.Text(
        string='Specification / Drawing Requirement',
    )
    evidence_notes = fields.Text(
        string='Evidence / Observations',
    )

    # ── CAP ───────────────────────────────────────────────────────────────────
    cap_description = fields.Text(string='Corrective Action Plan (CAP)')
    cap_rejection_reason = fields.Text(string='CAP Rejection Reason')
    rectification_description = fields.Text(string='Rectification Carried Out')
    verification_notes = fields.Text(string='QA Verification Notes')

    # ── RESUBMISSION COUNT ────────────────────────────────────────────────────
    cap_resubmission_count = fields.Integer(
        string='CAP Resubmissions', default=0, readonly=True,
    )

    # ── COMPUTES ──────────────────────────────────────────────────────────────
    CAP_DAYS = {'critical': 1, 'major': 3, 'minor': 7, 'observation': 14}


    @api.depends('contractor_party_id')
    def _compute_contractor_id(self):
        for rec in self:
            try:
                rec.contractor_id = rec.contractor_party_id.partner_id if rec.contractor_party_id else False
            except Exception:
                rec.contractor_id = False

    @api.depends('raised_date', 'severity')
    def _compute_cap_deadline(self):
        for rec in self:
            if rec.raised_date and rec.severity:
                days = self.CAP_DAYS.get(rec.severity, 7)
                rec.cap_response_deadline = rec.raised_date + timedelta(days=days)
            else:
                rec.cap_response_deadline = False

    @api.depends('raised_date', 'closed_date', 'state')
    def _compute_days_open(self):
        today = date.today()
        for rec in self:
            if rec.raised_date:
                end = rec.closed_date if rec.state == 'closed' and rec.closed_date else today
                rec.days_open = (end - rec.raised_date).days
            else:
                rec.days_open = 0

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'salaam.ncr'
                ) or 'New'
        return super().create(vals_list)

    @api.depends('name', 'title')
    def _compute_display_name(self):
        for rec in self:
            rec.display_name = f"{rec.name} — {rec.title}" if rec.title else rec.name

    # ── WORKFLOW ──────────────────────────────────────────────────────────────
    def action_submit_cap(self):
        for rec in self:
            if not rec.cap_description:
                raise UserError(_(
                    'Enter the Corrective Action Plan before submitting.'
                ))
            rec.state = 'cap_submitted'
            rec.cap_submitted_date = date.today()
            rec.message_post(body=_(
                'CAP submitted by %s on %s.'
            ) % (rec.contractor_id.name or '—', rec.cap_submitted_date))

    def action_approve_cap(self):
        for rec in self:
            rec.state = 'cap_approved'
            rec.cap_approved_date = date.today()
            if rec.work_stopped:
                rec.message_post(body=_(
                    'CAP approved. Work may resume in affected area.'
                ))
            # Auto-set rectification deadline
            days = {'critical': 3, 'major': 7, 'minor': 14, 'observation': 30}
            rec.rectification_deadline = date.today() + timedelta(
                days=days.get(rec.severity, 14)
            )

    def action_reject_cap(self):
        for rec in self:
            rec.state = 'cap_rejected'
            rec.cap_resubmission_count += 1
            rec.message_post(body=_(
                'CAP rejected. Resubmission #%d required. Reason: %s'
            ) % (rec.cap_resubmission_count, rec.cap_rejection_reason or '—'))

    def action_start_rectifying(self):
        self.state = 'rectifying'

    def action_submit_for_verification(self):
        for rec in self:
            if not rec.rectification_description:
                raise UserError(_(
                    'Describe the rectification carried out before submitting for verification.'
                ))
            rec.state = 'verification'
            rec.verification_date = date.today()

    def action_close(self):
        for rec in self:
            if not rec.verification_notes:
                raise UserError(_(
                    'Enter QA verification notes before closing the NCR.'
                ))
            rec.state = 'closed'
            rec.closed_date = date.today()
            rec.work_stopped = False
            rec.message_post(body=_(
                'NCR closed on %s. Conformance restored. Days open: %d.'
            ) % (rec.closed_date, rec.days_open))

    def action_reject_permanent(self):
        self.state = 'rejected_permanent'
