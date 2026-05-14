# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError
from datetime import date, timedelta


class SiteInstruction(models.Model):
    """
    Site Instruction (SI) / Engineer's Instruction (EI).

    A formal written direction issued by the Project Manager or Engineer
    to the Contractor. Every change to the works, every response to a
    design conflict, every urgent direction MUST be backed by a signed SI.

    Verbal instructions are not contractually binding. This model creates
    the formal paper trail that protects both parties.

    Types:
      scope_change      — changes to the agreed scope of works
      design_change     — architectural/engineering design change
      provisional_sum   — instruction to expend a provisional sum
      daywork           — instruction to carry out work on a daywork basis
      material_sub      — approved substitution of specified material
      acceleration      — instruction to accelerate works (cost implications)
      suspension        — instruction to suspend works (Employer risk)
      urgent_work       — emergency works instruction
      quality_remedy    — instruction to remedy defective work (NCR-driven)
      other             — catch-all

    Cost & Time implications:
      Each SI is assessed for cost impact (→ Variation / IPC)
      and time impact (→ EOT claim).

    Status flow:
      draft → issued → acknowledged → completed / disputed
    """
    _name = 'salaam.site.instruction'
    _description = 'Site Instruction'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'project_id, name desc'

    # ── IDENTITY ──────────────────────────────────────────────────────────────
    name = fields.Char(
        string='SI Reference', readonly=True, copy=False, default='New',
    )
    title = fields.Char(string='Instruction Title', required=True)
    state = fields.Selection([
        ('draft',        'Draft'),
        ('issued',       'Issued to Contractor'),
        ('acknowledged', 'Acknowledged by Contractor'),
        ('completed',    'Completed'),
        ('disputed',     'Disputed'),
    ], string='Status', default='draft', tracking=True)

    # ── CLASSIFICATION ────────────────────────────────────────────────────────
    instruction_type = fields.Selection([
        ('scope_change',   'Scope Change'),
        ('design_change',  'Design Change'),
        ('provisional_sum','Provisional Sum Expenditure'),
        ('daywork',        'Daywork Authorisation'),
        ('material_sub',   'Material Substitution'),
        ('acceleration',   'Acceleration Instruction'),
        ('suspension',     'Works Suspension'),
        ('urgent_work',    'Urgent / Emergency Works'),
        ('quality_remedy', 'Quality Remedy — NCR-Driven'),
        ('other',          'Other'),
    ], string='Instruction Type', required=True)

    priority = fields.Selection([
        ('routine',   'Routine'),
        ('urgent',    'Urgent — 48h compliance'),
        ('immediate', 'Immediate — Stop / Start Now'),
    ], string='Priority', default='routine', tracking=True)

    # ── LINKS ─────────────────────────────────────────────────────────────────
    project_id = fields.Many2one(
        'salaam.construction.project',
        string='Construction Project', required=True, index=True,
    )
    phase_id = fields.Many2one(
        'salaam.construction.phase',
        string='Affected Phase',
    )
    # contractor_party_id = fields.Many2one(
    #     'salaam.project.party',
    #     string='Issued To (Contractor)',
    # )
    contractor_party_id = fields.Many2one(
        'res.partner',
        string='Issued To (Contractor)',
    )
    contractor_id = fields.Many2one(
        'res.partner', string='Contractor',
        compute='_compute_contractor_id', store=True,
    )
    issued_by = fields.Many2one(
        'res.users', string='Issued By',
        default=lambda self: self.env.user,
    )
    ncr_id = fields.Many2one(
        'salaam.ncr',
        string='Related NCR',
        help='If this SI is issued to remedy an NCR',
    )
    drawing_ref = fields.Char(string='Related Drawing Reference')
    rfi_ref = fields.Char(string='Related RFI Reference')

    # ── DATES ─────────────────────────────────────────────────────────────────
    issue_date = fields.Date(
        string='Issue Date', default=fields.Date.today,
    )
    compliance_deadline = fields.Date(
        string='Compliance Deadline',
        compute='_compute_compliance_deadline', store=True,
    )
    acknowledged_date = fields.Date(string='Date Acknowledged')
    completed_date = fields.Date(string='Date Completed')

    # ── INSTRUCTION CONTENT ───────────────────────────────────────────────────
    description = fields.Html(string='Instruction Details', required=True)
    scope_of_works = fields.Text(string='Scope of Works Instructed')

    # ── COST IMPACT ───────────────────────────────────────────────────────────
    has_cost_impact = fields.Boolean(string='Cost Impact?', default=False)
    currency_id = fields.Many2one(
        'res.currency', default=lambda self: self.env.company.currency_id,
    )
    estimated_cost = fields.Monetary(
        string='Estimated Cost Impact',
        currency_field='currency_id',
    )
    agreed_cost = fields.Monetary(
        string='Agreed Cost',
        currency_field='currency_id',
    )
    cost_basis = fields.Selection([
        ('lump_sum',   'Agreed Lump Sum'),
        ('daywork',    'Daywork Rates'),
        ('schedule',   'Schedule of Rates'),
        ('cost_plus',  'Cost Plus'),
        ('tbd',        'To Be Determined'),
    ], string='Cost Basis', default='tbd')
    ipc_id = fields.Many2one(
        'salaam.payment.certificate',
        string='Included in IPC',
        help='The IPC in which this SI cost was certified',
    )

    # ── TIME IMPACT ───────────────────────────────────────────────────────────
    has_time_impact = fields.Boolean(string='Time Impact?', default=False)
    estimated_delay_days = fields.Integer(string='Estimated Delay (days)')
    eot_claim_id = fields.Many2one(
        'salaam.eot.claim',
        string='Related EOT Claim',
        help='EOT claim submitted by contractor as a result of this SI',
    )

    # ── CONTRACTOR RESPONSE ───────────────────────────────────────────────────
    contractor_response = fields.Text(string='Contractor Response / Comments')
    dispute_reason = fields.Text(string='Dispute Reason')

    # ── COMPUTES ──────────────────────────────────────────────────────────────

    @api.depends('contractor_party_id')
    def _compute_contractor_id(self):
        for rec in self:
            try:
                rec.contractor_id = rec.contractor_party_id.partner_id if rec.contractor_party_id else False
            except Exception:
                rec.contractor_id = False

    @api.depends('issue_date', 'priority')
    def _compute_compliance_deadline(self):
        for rec in self:
            if rec.issue_date:
                days = {'routine': 14, 'urgent': 2, 'immediate': 0}
                rec.compliance_deadline = (
                    rec.issue_date + timedelta(days=days.get(rec.priority, 14))
                )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'salaam.site.instruction'
                ) or 'New'
        return super().create(vals_list)

    @api.depends('name', 'title')
    def _compute_display_name(self):
        for rec in self:
            rec.display_name = f"{rec.name} — {rec.title}" if rec.title else rec.name

    # ── WORKFLOW ──────────────────────────────────────────────────────────────
    def action_issue(self):
        for rec in self:
            if not rec.contractor_party_id:
                raise UserError(_(
                    'Select the contractor party before issuing the instruction.'
                ))
            rec.state = 'issued'
            rec.issue_date = date.today()
            rec.message_post(body=_(
                'Site Instruction %s issued to %s. '
                'Compliance deadline: %s. Priority: %s.'
            ) % (rec.name, rec.contractor_id.name,
                 rec.compliance_deadline, rec.priority))

    def action_acknowledge(self):
        self.write({
            'state': 'acknowledged',
            'acknowledged_date': date.today(),
        })

    def action_complete(self):
        self.write({
            'state': 'completed',
            'completed_date': date.today(),
        })

    def action_dispute(self):
        self.state = 'disputed'

    def action_reset_draft(self):
        self.state = 'draft'
