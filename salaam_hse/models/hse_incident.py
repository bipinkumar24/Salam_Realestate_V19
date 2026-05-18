# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError
from datetime import date


# ── MODEL 1: HSE INCIDENT ─────────────────────────────────────────────────────

class HSEIncident(models.Model):
    """
    Site incident log — Djibouti regulatory compliance.

    Incident types follow RIDDOR-equivalent classification:
      near_miss           — no injury, potential for harm
      first_aid           — treated on site, no lost time
      lost_time           — worker unable to return to work next shift
      dangerous_occurrence — structural failure, fire, explosion, etc.
      fatality            — death on site

    Notification requirements:
      lost_time + dangerous_occurrence + fatality → immediate IAFAO notification
      fatality → regulatory authority (Djibouti Ministry of Labour) notification

    Status: reported → investigating → closed / escalated
    """
    _name = 'salaam.hse.incident'
    _description = 'HSE Incident'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'incident_datetime desc'

    name = fields.Char(
        string='Incident Reference', readonly=True,
        copy=False, default='New',
    )
    state = fields.Selection([
        ('reported',      'Reported'),
        ('investigating', 'Under Investigation'),
        ('closed',        'Closed'),
        ('escalated',     'Escalated — Regulatory'),
    ], string='Status', default='reported', tracking=True)

    # ── LINKS ─────────────────────────────────────────────────────────────────
    project_id = fields.Many2one(
        'project.project', required=True, index=True,
    )
    phase_id = fields.Many2one(
        'buruuj.phase',
    )
    contractor_id = fields.Many2one('res.partner', string='Contractor on Site')
    reported_by = fields.Many2one(
        'res.users', string='Reported By', default=lambda self: self.env.user,
    )
    investigator_id = fields.Many2one('res.users', string='Lead Investigator')

    # ── INCIDENT DETAILS ──────────────────────────────────────────────────────
    incident_type = fields.Selection([
        ('near_miss',           'Near Miss'),
        ('first_aid',           'First Aid'),
        ('lost_time',           'Lost Time Injury (LTI)'),
        ('dangerous_occurrence','Dangerous Occurrence'),
        ('fatality',            'Fatality'),
        ('environmental',       'Environmental Incident'),
        ('property_damage',     'Property Damage'),
        ('fire',                'Fire / Explosion'),
    ], string='Incident Type', required=True, tracking=True)

    incident_datetime = fields.Datetime(
        string='Date & Time of Incident', required=True,
        default=fields.Datetime.now,
    )
    location_description = fields.Char(string='Location on Site')
    description = fields.Text(string='Incident Description', required=True)

    # ── INJURED PARTY ─────────────────────────────────────────────────────────
    injured_party_name = fields.Char(string='Injured Party Name')
    injured_party_employer = fields.Char(string='Injured Party Employer')
    injury_description = fields.Text(string='Nature of Injury')
    lost_time_days = fields.Integer(string='Lost Time Days')
    hospital_attended = fields.Boolean(string='Hospital Attended')

    # ── IMMEDIATE ACTIONS ─────────────────────────────────────────────────────
    immediate_actions = fields.Text(string='Immediate Actions Taken')
    work_stopped = fields.Boolean(
        string='Work Stopped in Affected Area', default=False,
    )
    iafao_notified = fields.Boolean(string='IAFAO Notified', default=False)
    iafao_notification_date = fields.Datetime(string='IAFAO Notification Date/Time')
    regulatory_notified = fields.Boolean(string='Regulatory Authority Notified')
    regulatory_notification_date = fields.Date(string='Regulatory Notification Date')

    # ── INVESTIGATION ─────────────────────────────────────────────────────────
    root_cause = fields.Text(string='Root Cause Analysis')
    contributing_factors = fields.Text(string='Contributing Factors')
    corrective_actions = fields.Text(string='Corrective Actions Required')
    preventive_measures = fields.Text(string='Preventive Measures')
    investigation_closed_date = fields.Date(string='Investigation Closed Date')

    # ── CLASSIFICATION ────────────────────────────────────────────────────────
    requires_immediate_notification = fields.Boolean(
        compute='_compute_notification_required', store=True,
    )

    @api.depends('incident_type')
    def _compute_notification_required(self):
        notify_types = {'lost_time', 'dangerous_occurrence', 'fatality', 'fire'}
        for rec in self:
            rec.requires_immediate_notification = rec.incident_type in notify_types


    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code(
                   'salaam.hse.incident'
                ) or _('New')
        return super().create(vals_list)


    def action_investigate(self):
        self.state = 'investigating'

    def action_close(self):
        for rec in self:
            if not rec.root_cause:
                raise UserError(_('Complete root cause analysis before closing the incident.'))
            rec.state = 'closed'
            rec.investigation_closed_date = date.today()

    def action_escalate(self):
        self.state = 'escalated'


# ── MODEL 2: METHOD STATEMENT (RAMS) ─────────────────────────────────────────

class HSEMethodStatement(models.Model):
    """
    Method Statement / RAMS (Risk Assessment and Method Statement) register.
    Must be approved before the linked work activity commences.
    """
    _name = 'salaam.hse.method.statement'
    _description = 'HSE Method Statement / RAMS'
    _inherit = ['mail.thread']
    _order = 'project_id, submission_date desc'

    name = fields.Char(
        string='RAMS Reference', readonly=True, copy=False, default='New',
    )
    title = fields.Char(string='Work Activity Title', required=True)
    state = fields.Selection([
        ('draft',    'Draft'),
        ('submitted','Submitted for Approval'),
        ('approved', 'Approved — Work May Commence'),
        ('rejected', 'Rejected — Revise & Resubmit'),
        ('superseded','Superseded'),
    ], string='Status', default='draft', tracking=True)

    project_id = fields.Many2one(
        'project.project', required=True, index=True,
    )
    phase_id = fields.Many2one(
        'buruuj.phase',
    )
    contractor_id = fields.Many2one('res.partner', string='Submitting Contractor')
    submitted_by = fields.Many2one('res.users', string='Submitted By')
    reviewer_id = fields.Many2one('res.users', string='HSE Reviewer')
    approved_by = fields.Many2one('res.users', string='Approved By')

    work_description = fields.Text(string='Description of Work Activity')
    hazards_identified = fields.Text(string='Hazards Identified')
    risk_controls = fields.Text(string='Risk Control Measures')
    ppe_required = fields.Text(string='PPE Requirements')
    emergency_procedure = fields.Text(string='Emergency Procedure')

    submission_date = fields.Date(string='Submission Date', default=fields.Date.today)
    approval_date = fields.Date(string='Approval Date')
    valid_until = fields.Date(string='Valid Until')
    rejection_reason = fields.Text(string='Rejection Reason')

    
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code(
                   'salaam.hse.method.statement'
                ) or _('New')
        return super().create(vals_list)

    def action_submit(self):
        self.write({'state': 'submitted', 'submitted_by': self.env.user.id})

    def action_approve(self):
        self.write({
            'state': 'approved',
            'approved_by': self.env.user.id,
            'approval_date': date.today(),
        })

    def action_reject(self):
        self.state = 'rejected'


# ── MODEL 3: TOOLBOX TALK ─────────────────────────────────────────────────────

class HSEToolboxTalk(models.Model):
    """
    Toolbox talk record — weekly safety briefings on site.
    Tracks attendance and topic coverage.
    """
    _name = 'salaam.hse.toolbox.talk'
    _description = 'HSE Toolbox Talk'
    _order = 'project_id, talk_date desc'

    name = fields.Char(
        string='Reference', readonly=True, copy=False, default='New',
    )
    project_id = fields.Many2one(
        'project.project', required=True, index=True,
    )
    phase_id = fields.Many2one(
        'buruuj.phase',
    )
    contractor_id = fields.Many2one('res.partner', string='Contractor Group')
    conductor_id = fields.Many2one(
        'res.users', string='Talk Conducted By', default=lambda self: self.env.user,
    )

    talk_date = fields.Date(
        string='Date', required=True, default=fields.Date.today,
    )
    topic = fields.Char(string='Topic / Subject', required=True)
    topic_category = fields.Selection([
        ('working_at_height', 'Working at Height'),
        ('lifting_ops',       'Lifting Operations'),
        ('excavation',        'Excavation & Trenching'),
        ('fire_prevention',   'Fire Prevention'),
        ('electrical',        'Electrical Safety'),
        ('ppe',               'PPE Requirements'),
        ('manual_handling',   'Manual Handling'),
        ('chemical',          'Hazardous Substances / COSHH'),
        ('emergency',         'Emergency Procedures'),
        ('traffic',           'Site Traffic Management'),
        ('heat_stress',       'Heat Stress (Djibouti climate)'),
        ('welfare',           'Welfare & Sanitation'),
        ('environmental',     'Environmental Protection'),
        ('other',             'Other'),
    ], string='Topic Category')

    attendee_count = fields.Integer(string='Number of Attendees', required=True)
    duration_minutes = fields.Integer(string='Duration (minutes)', default=15)
    language = fields.Selection([
        ('arabic',  'Arabic'),
        ('french',  'French'),
        ('somali',  'Somali'),
        ('english', 'English'),
        ('other',   'Other'),
    ], string='Language', default='arabic')

    content_summary = fields.Text(string='Content Summary / Key Points')
    actions_arising = fields.Text(string='Actions Arising')
    attendance_list = fields.Text(
        string='Attendance List (names / signatures)',
        help='Names and trade of workers who attended',
    )

   
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code(
                   'salaam.hse.toolbox.talk'
                ) or _('New')
        return super().create(vals_list)


# ── MODEL 4: HSE AUDIT ────────────────────────────────────────────────────────

class HSEAudit(models.Model):
    """
    Periodic HSE audit record.
    Internal / External / Regulatory audit types.
    Findings with corrective action tracking.
    """
    _name = 'salaam.hse.audit'
    _description = 'HSE Audit'
    _inherit = ['mail.thread']
    _order = 'project_id, audit_date desc'

    name = fields.Char(
        string='Audit Reference', readonly=True, copy=False, default='New',
    )
    state = fields.Selection([
        ('planned',         'Planned'),
        ('conducted',       'Conducted'),
        ('findings_issued', 'Findings Issued'),
        ('closed',          'Closed'),
    ], string='Status', default='planned', tracking=True)

    project_id = fields.Many2one(
        'project.project', required=True, index=True,
    )
    audit_type = fields.Selection([
        ('internal',    'Internal HSE Audit'),
        ('external',    'External / Third-Party Audit'),
        ('regulatory',  'Regulatory Authority Inspection'),
        ('lender',      'Lender / Financier HSE Review'),
        ('insurance',   'Insurance Inspection'),
    ], string='Audit Type', required=True)

    auditor_id = fields.Many2one('res.users', string='Lead Auditor')
    auditor_organisation = fields.Char(string='Auditing Organisation')
    audit_date = fields.Date(string='Audit Date', required=True, default=fields.Date.today)
    findings_issued_date = fields.Date(string='Findings Issued Date')
    response_deadline = fields.Date(string='Response Deadline')
    closed_date = fields.Date(string='Closed Date')

    scope = fields.Text(string='Audit Scope')
    findings = fields.Text(string='Audit Findings')
    corrective_actions = fields.Text(string='Required Corrective Actions')
    overall_rating = fields.Selection([
        ('satisfactory',  'Satisfactory'),
        ('improvement',   'Improvement Needed'),
        ('unsatisfactory','Unsatisfactory'),
        ('stop_work',     'Stop Work Order Issued'),
    ], string='Overall Rating')

    critical_findings = fields.Integer(string='Critical Findings', default=0)
    major_findings = fields.Integer(string='Major Findings', default=0)
    minor_findings = fields.Integer(string='Minor Findings', default=0)
    observations = fields.Integer(string='Observations', default=0)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code(
                   'salaam.hse.audit'
                ) or _('New')
        return super().create(vals_list)

    def action_conduct(self):
        self.state = 'conducted'

    def action_issue_findings(self):
        self.write({'state': 'findings_issued', 'findings_issued_date': date.today()})

    def action_close(self):
        self.write({'state': 'closed', 'closed_date': date.today()})
