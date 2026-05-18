# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError
from datetime import date


class Tender(models.Model):
    """
    Tender master record per construction package.
    Covers the pre-contract procurement phase for all delivery methods
    that require competitive bidding (DBB, CMAR, CMMP, EPC).

    Types:
      open        — public advertising, any qualified contractor
      selective   — invitation-only, pre-qualified list
      negotiated  — single source, negotiated price
      framework   — call-offs against a pre-agreed framework

    Status: draft → published → closed → evaluation → awarded / cancelled
    """
    _name = 'salaam.tender'
    _description = 'Tender'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'issue_date desc'

    # ── IDENTITY ──────────────────────────────────────────────────────────────
    name = fields.Char(string='Tender Reference', readonly=True,
                       copy=False, default='New')
    title = fields.Char(string='Tender Title', required=True)
    state = fields.Selection([
        ('draft',      'Draft'),
        ('published',  'Published / Issued'),
        ('closed',     'Submission Closed'),
        ('evaluation', 'Under Evaluation'),
        ('awarded',    'Awarded'),
        ('cancelled',  'Cancelled'),
    ], string='Status', default='draft', tracking=True)

    # ── CLASSIFICATION ────────────────────────────────────────────────────────
    tender_type = fields.Selection([
        ('open',       'Open Tender'),
        ('selective',  'Selective / Invited Tender'),
        ('negotiated', 'Negotiated / Single Source'),
        ('framework',  'Framework Agreement Call-Off'),
    ], string='Tender Type', required=True, default='selective')

    package_type = fields.Selection([
        ('main_contract',   'Main Contract'),
        ('subcontract',     'Subcontract Package'),
        ('design',          'Design / Consultancy'),
        ('specialist',      'Specialist Works'),
        ('supply',          'Supply Only'),
        ('epc',             'EPC / Turnkey'),
    ], string='Contract Package Type', required=True)

    delivery_method_code = fields.Selection([
        ('dbb', 'DBB'), ('db', 'DB'), ('cmar', 'CMAR'),
        ('cmmp', 'CMMP'), ('epc', 'EPC'), ('ipd', 'IPD'), ('ppp', 'PPP'),
    ], string='Delivery Method')

    # ── LINKS ─────────────────────────────────────────────────────────────────
    project_id = fields.Many2one(
        'project.project',
        string='Construction Project', required=True, index=True,
    )
    phase_id = fields.Many2one(
        'buruuj.phase',
        string='Construction Phase',
    )
    awarded_contract_ref = fields.Reference(
        selection=[
            ('dev.contract.istisna',       'Istisna Contract'),
            ('dev.contract.subcontractor', 'Subcontractor Agreement'),
            ('dev.contract.consultancy',   'Consultancy Agreement'),
        ],
        string='Awarded Contract Record',
        help='Link to the contract record created after award',
    )

    # ── SCOPE ─────────────────────────────────────────────────────────────────
    scope_description = fields.Html(string='Scope of Works / Services')
    currency_id = fields.Many2one(
        'res.currency', default=lambda self: self.env.company.currency_id,
    )
    estimated_value = fields.Monetary(
        string='Estimated Contract Value',
        currency_field='currency_id',
    )
    bid_bond_required = fields.Boolean(string='Bid Bond Required', default=True)
    bid_bond_pct = fields.Float(string='Bid Bond (%)', default=2.5)
    performance_bond_pct = fields.Float(string='Performance Bond (%)', default=10.0)
    retention_pct = fields.Float(string='Retention (%)', default=5.0)
    dlp_months = fields.Integer(string='Defect Liability Period (months)', default=12)
    sharia_compliance_required = fields.Boolean(
        string='Sharia Compliance Mandatory',
        default=True,
        help='Tenderer must confirm Sharia-compliant subcontracting and supply chain',
    )

    # ── DATES ─────────────────────────────────────────────────────────────────
    issue_date = fields.Date(string='Tender Issue Date', default=fields.Date.today)
    site_visit_date = fields.Date(string='Mandatory Site Visit Date')
    clarification_deadline = fields.Date(string='Clarification Deadline')
    submission_deadline = fields.Date(
        string='Submission Deadline', required=True, tracking=True,
    )
    evaluation_start = fields.Date(string='Evaluation Start Date')
    award_date = fields.Date(string='Award Date')

    # ── INVITEES / BIDS ───────────────────────────────────────────────────────
    invitee_ids = fields.One2many(
        'salaam.tender.invitee', 'tender_id', string='Tenderers / Bids',
    )
    invitee_count = fields.Integer(compute='_compute_invitee_count')
    submitted_count = fields.Integer(compute='_compute_invitee_count')
    awarded_invitee_id = fields.Many2one(
        'salaam.tender.invitee',
        string='Awarded To',
        domain="[('tender_id','=',id),('bid_submitted','=',True)]",
    )
    awarded_amount = fields.Monetary(
        string='Awarded Amount',
        currency_field='currency_id',
    )

    # ── EVALUATION CRITERIA WEIGHTS ───────────────────────────────────────────
    weight_technical = fields.Float(string='Technical Weight (%)', default=40.0)
    weight_commercial = fields.Float(string='Commercial Weight (%)', default=30.0)
    weight_sharia = fields.Float(string='Sharia Compliance Weight (%)', default=15.0)
    weight_hse = fields.Float(string='HSE Weight (%)', default=10.0)
    weight_local = fields.Float(string='Local Content Weight (%)', default=5.0)

    notes = fields.Text(string='Tender Notes / Special Conditions')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'salaam.tender'
                ) or _('New')
        return super().create(vals_list)

    @api.depends('invitee_ids', 'invitee_ids.bid_submitted')
    def _compute_invitee_count(self):
        for rec in self:
            rec.invitee_count = len(rec.invitee_ids)
            rec.submitted_count = len(rec.invitee_ids.filtered('bid_submitted'))

    def action_publish(self):
        for rec in self:
            if not rec.submission_deadline:
                raise UserError(_('Set a submission deadline before publishing.'))
            rec.state = 'published'

    def action_close_submissions(self):
        self.state = 'closed'

    def action_start_evaluation(self):
        self.write({'state': 'evaluation', 'evaluation_start': date.today()})

    def action_award(self):
        for rec in self:
            if not rec.awarded_invitee_id:
                raise UserError(_('Select the awarded tenderer before confirming award.'))
            rec.state = 'awarded'
            rec.award_date = date.today()
            rec.awarded_amount = rec.awarded_invitee_id.bid_amount
            rec.message_post(body=_(
                'Tender AWARDED to %s. Amount: %s %s'
            ) % (rec.awarded_invitee_id.partner_id.name,
                 rec.awarded_amount, rec.currency_id.symbol))

    def action_cancel(self):
        self.state = 'cancelled'


class TenderInvitee(models.Model):
    """Invited tenderer — tracks bid submission, qualification, and evaluation."""
    _name = 'salaam.tender.invitee'
    _description = 'Tender Invitee'
    _order = 'tender_id, evaluation_rank'

    tender_id = fields.Many2one(
        'salaam.tender', required=True, ondelete='cascade', index=True,
    )
    partner_id = fields.Many2one(
        'res.partner', string='Contractor / Firm', required=True,
    )
    currency_id = fields.Many2one(related='tender_id.currency_id', store=True)

    # ── QUALIFICATION ─────────────────────────────────────────────────────────
    qualified = fields.Boolean(string='Pre-Qualified', default=True)
    disqualification_reason = fields.Char(string='Disqualification Reason')
    bid_bond_submitted = fields.Boolean(string='Bid Bond Submitted')

    # ── SUBMISSION ────────────────────────────────────────────────────────────
    bid_submitted = fields.Boolean(string='Bid Submitted', default=False)
    submission_date = fields.Date(string='Submission Date')
    bid_amount = fields.Monetary(string='Bid Amount', currency_field='currency_id')
    bid_validity_days = fields.Integer(
        string='Bid Validity (days)', default=90,
    )

    # ── EVALUATION SCORES ─────────────────────────────────────────────────────
    score_technical = fields.Float(string='Technical Score (0–100)', digits=(5, 1))
    score_commercial = fields.Float(string='Commercial Score (0–100)', digits=(5, 1))
    score_sharia = fields.Float(string='Sharia Compliance Score (0–100)', digits=(5, 1))
    score_hse = fields.Float(string='HSE Score (0–100)', digits=(5, 1))
    score_local = fields.Float(string='Local Content Score (0–100)', digits=(5, 1))

    weighted_score = fields.Float(
        string='Weighted Score (%)',
        compute='_compute_weighted', store=True, digits=(5, 2),
    )
    evaluation_rank = fields.Integer(
        string='Rank', compute='_compute_rank', store=True,
    )
    recommendation = fields.Selection([
        ('recommend',    'Recommend for Award'),
        ('acceptable',   'Acceptable — Not Preferred'),
        ('not_recommend','Do Not Recommend'),
    ], compute='_compute_weighted', store=True)

    notes = fields.Text(string='Evaluation Notes')

    @api.depends(
        'score_technical', 'score_commercial', 'score_sharia',
        'score_hse', 'score_local',
        'tender_id.weight_technical', 'tender_id.weight_commercial',
        'tender_id.weight_sharia', 'tender_id.weight_hse', 'tender_id.weight_local',
    )
    def _compute_weighted(self):
        for rec in self:
            t = rec.tender_id
            total = (
                rec.score_technical  * (t.weight_technical  / 100) +
                rec.score_commercial * (t.weight_commercial / 100) +
                rec.score_sharia     * (t.weight_sharia     / 100) +
                rec.score_hse        * (t.weight_hse        / 100) +
                rec.score_local      * (t.weight_local      / 100)
            )
            rec.weighted_score = round(total, 2)
            rec.recommendation = (
                'recommend' if total >= 70 else
                'acceptable' if total >= 50 else
                'not_recommend'
            )

    @api.depends('weighted_score', 'tender_id.invitee_ids.weighted_score')
    def _compute_rank(self):
        for rec in self:
            higher = rec.tender_id.invitee_ids.filtered(
                lambda i: i.id != rec.id and i.weighted_score > rec.weighted_score
            )
            rec.evaluation_rank = len(higher) + 1
