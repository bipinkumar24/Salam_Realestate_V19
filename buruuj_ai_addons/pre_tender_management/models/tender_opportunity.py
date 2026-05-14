# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError


class CrmLead(models.Model):
    _inherit = 'crm.lead'

    is_tender = fields.Boolean(string='Is Tender', default=False, tracking=True)
    tender_reference = fields.Char(string='Tender Reference', copy=False, tracking=True)
    client_id = fields.Many2one(
        'res.partner', string='Issuing Entity',
        domain="[('is_company', '=', True)]", tracking=True,
    )
    funding_source = fields.Selection([
        ('government', 'Government'),
        ('private', 'Private'),
        ('donor', 'Donor / NGO'),
        ('ifi', 'International Financial Institution'),
        ('mixed', 'Mixed / Blended'),
    ], string='Funding Source', tracking=True)
    tender_value_estimate = fields.Monetary(
        string='Tender Value (Estimated)',
        currency_field='company_currency', tracking=True,
    )
    submission_deadline = fields.Datetime(string='Submission Deadline', tracking=True)
    submission_method = fields.Selection([
        ('portal', 'E-Procurement Portal'),
        ('hardcopy', 'Hardcopy / Courier'),
        ('email', 'Email'),
        ('inperson', 'In-Person'),
    ], string='Submission Method', tracking=True)

    pwin_manual = fields.Float(string='Pwin Manual %', tracking=True)
    pwin_ai = fields.Float(
        string='Pwin AI %', readonly=True,
        help='Computed by Odoo AI lead qualification (Phase 5).',
    )

    eligibility_state = fields.Selection([
        ('pending', 'Pending'),
        ('pass', 'Pass'),
        ('fail', 'Fail'),
    ], string='Eligibility', default='pending', tracking=True)
    incumbent_id = fields.Many2one(
        'res.partner', string='Incumbent',
        domain="[('is_company', '=', True)]",
    )
    is_wired_tender = fields.Boolean(string='Wired Tender', tracking=True)
    wired_tender_justification = fields.Text(string='Wired Tender Justification')

    required_certificate_ids = fields.Many2many(
        'tender.compliance.certificate',
        'tender_lead_certificate_rel', 'lead_id', 'certificate_id',
        string='Required Certificates',
    )
    compliance_matrix_id = fields.Many2one(
        'tender.compliance.matrix', string='Compliance Matrix',
        copy=False,
    )
    compliance_progress = fields.Float(
        string='Compliance %', related='compliance_matrix_id.progress',
        store=True, readonly=True,
    )
    bid_decision_ids = fields.One2many(
        'tender.bid.decision', 'opportunity_id', string='Bid Decisions',
    )
    latest_bid_decision_id = fields.Many2one(
        'tender.bid.decision', compute='_compute_latest_bid_decision', store=True,
    )
    bid_decision_state = fields.Selection(
        related='latest_bid_decision_id.state', store=True, readonly=True,
    )

    bid_bond_ids = fields.One2many('tender.bid.bond', 'opportunity_id', string='Bid Bonds')
    bid_bond_count = fields.Integer(compute='_compute_related_counts')
    site_survey_ids = fields.One2many('tender.site.survey', 'opportunity_id', string='Site Surveys')
    site_survey_count = fields.Integer(compute='_compute_related_counts')
    site_survey_done = fields.Boolean(compute='_compute_related_counts', store=True)

    capture_plan_id = fields.Many2one('tender.capture.plan', string='Capture Plan', copy=False)
    risk_ids = fields.One2many('tender.risk', 'opportunity_id', string='Risks')
    risk_count = fields.Integer(compute='_compute_related_counts')
    high_risk_count = fields.Integer(compute='_compute_related_counts')

    partner_agreement_ids = fields.One2many('tender.partner.agreement', 'opportunity_id', string='Partner Agreements')
    partner_agreement_count = fields.Integer(compute='_compute_related_counts')
    budget_quote_ids = fields.One2many('tender.budget.quote', 'opportunity_id', string='Budget Quotes')
    budget_quote_count = fields.Integer(compute='_compute_related_counts')

    stakeholder_ids = fields.One2many('tender.stakeholder', 'opportunity_id', string='Stakeholders')
    stakeholder_count = fields.Integer(compute='_compute_related_counts')
    clarification_ids = fields.One2many('tender.clarification', 'opportunity_id', string='Clarifications')
    clarification_count = fields.Integer(compute='_compute_related_counts')
    prebid_meeting_ids = fields.One2many('tender.prebid.meeting', 'opportunity_id', string='Pre-Bid Meetings')
    prebid_meeting_count = fields.Integer(compute='_compute_related_counts')

    bid_team_member_ids = fields.One2many('tender.bid.team.member', 'opportunity_id', string='Bid Team')
    bid_team_count = fields.Integer(compute='_compute_related_counts')

    competitor_link_ids = fields.One2many(
        'tender.opportunity.competitor', 'opportunity_id', string='Competitive Landscape',
    )
    competitor_count = fields.Integer(compute='_compute_related_counts')

    kickoff_gate_ids = fields.One2many('tender.kickoff.gate', 'opportunity_id', string='Review Gates')
    kickoff_gate_count = fields.Integer(compute='_compute_related_counts')

    swot_ids = fields.One2many('tender.swot', 'opportunity_id', string='SWOT Analyses')

    tier2_progress = fields.Float(
        string='Tier 2 Progress %', compute='_compute_tier_progress', store=True,
    )
    tier2_complete = fields.Boolean(compute='_compute_tier_progress', store=True)
    tier3_progress = fields.Float(
        string='Tier 3 Progress %', compute='_compute_tier_progress', store=True,
    )

    qualification_complete = fields.Boolean(
        compute='_compute_tier1', store=True,
    )
    tier1_complete = fields.Boolean(
        string='Tier 1 Complete', compute='_compute_tier1', store=True, tracking=True,
    )
    tier1_progress = fields.Float(
        string='Tier 1 Progress %', compute='_compute_tier1', store=True,
    )

    tender_state = fields.Selection([
        ('draft', 'Lead'),
        ('qualified', 'Qualified'),
        ('bid_decision', 'Bid Decision'),
        ('no_bid', 'No-Bid'),
        ('capture', 'Capture'),
        ('kickoff', 'Kickoff'),
        ('submitted', 'Submitted'),
        ('won', 'Won'),
        ('lost', 'Lost'),
        ('withdrawn', 'Withdrawn'),
    ], default='draft', tracking=True, copy=False, group_expand='_group_expand_tender_state')

    @api.model
    def _group_expand_tender_state(self, states, domain, order=None):
        return [s[0] for s in self._fields['tender_state'].selection]

    @api.depends('bid_decision_ids', 'bid_decision_ids.state', 'bid_decision_ids.decision_date')
    def _compute_latest_bid_decision(self):
        for rec in self:
            rec.latest_bid_decision_id = rec.bid_decision_ids[:1]

    @api.depends(
        'bid_bond_ids', 'site_survey_ids', 'site_survey_ids.state',
        'risk_ids', 'risk_ids.severity',
        'partner_agreement_ids', 'budget_quote_ids',
        'stakeholder_ids', 'clarification_ids', 'prebid_meeting_ids',
        'bid_team_member_ids', 'competitor_link_ids', 'kickoff_gate_ids',
    )
    def _compute_related_counts(self):
        for rec in self:
            rec.bid_bond_count = len(rec.bid_bond_ids)
            rec.site_survey_count = len(rec.site_survey_ids)
            rec.site_survey_done = bool(rec.site_survey_ids.filtered(
                lambda s: s.state in ('done', 'waived')
            ))
            rec.risk_count = len(rec.risk_ids)
            rec.high_risk_count = len(rec.risk_ids.filtered(
                lambda r: r.severity in ('high', 'critical')
            ))
            rec.partner_agreement_count = len(rec.partner_agreement_ids)
            rec.budget_quote_count = len(rec.budget_quote_ids)
            rec.stakeholder_count = len(rec.stakeholder_ids)
            rec.clarification_count = len(rec.clarification_ids)
            rec.prebid_meeting_count = len(rec.prebid_meeting_ids)
            rec.bid_team_count = len(rec.bid_team_member_ids)
            rec.competitor_count = len(rec.competitor_link_ids)
            rec.kickoff_gate_count = len(rec.kickoff_gate_ids)

    @api.depends(
        'capture_plan_id', 'risk_ids', 'partner_agreement_ids',
        'stakeholder_ids', 'bid_team_member_ids', 'budget_quote_ids',
        'competitor_link_ids', 'kickoff_gate_ids',
    )
    def _compute_tier_progress(self):
        for rec in self:
            tier2_checks = [
                bool(rec.capture_plan_id),
                bool(rec.risk_ids),
                bool(rec.bid_team_member_ids),
                bool(rec.stakeholder_ids),
                bool(rec.partner_agreement_ids) or bool(rec.budget_quote_ids),
            ]
            rec.tier2_progress = (sum(1 for c in tier2_checks if c) / len(tier2_checks)) * 100.0
            rec.tier2_complete = all(tier2_checks)
            tier3_checks = [
                bool(rec.competitor_link_ids),
                bool(rec.kickoff_gate_ids),
            ]
            rec.tier3_progress = (sum(1 for c in tier3_checks if c) / len(tier3_checks)) * 100.0

    @api.depends(
        'eligibility_state', 'pwin_manual',
        'compliance_progress', 'bid_decision_state',
        'site_survey_done',
    )
    def _compute_tier1(self):
        for rec in self:
            qual_ok = rec.eligibility_state == 'pass' and rec.pwin_manual > 0
            comp_ok = rec.compliance_progress >= 100.0
            decision_ok = rec.bid_decision_state == 'approved'
            survey_ok = rec.site_survey_done
            checks = [qual_ok, comp_ok, decision_ok, survey_ok]
            rec.qualification_complete = qual_ok
            rec.tier1_complete = all(checks)
            rec.tier1_progress = (sum(1 for c in checks if c) / len(checks)) * 100.0

    def action_open_compliance_matrix(self):
        self.ensure_one()
        matrix = self.compliance_matrix_id
        if not matrix:
            matrix = self.env['tender.compliance.matrix'].create({
                'opportunity_id': self.id,
                'name': f'Compliance — {self.name}',
            })
            self.compliance_matrix_id = matrix.id
        return {
            'type': 'ir.actions.act_window',
            'name': _('Compliance Matrix'),
            'res_model': 'tender.compliance.matrix',
            'res_id': matrix.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_view_bid_decisions(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Bid / No-Bid Decisions'),
            'res_model': 'tender.bid.decision',
            'view_mode': 'list,form',
            'domain': [('opportunity_id', '=', self.id)],
            'context': {'default_opportunity_id': self.id},
        }

    def action_set_qualified(self):
        for rec in self:
            if rec.eligibility_state != 'pass':
                raise UserError(_('Eligibility must be Pass before qualifying the opportunity.'))
            if not rec.pwin_manual:
                raise UserError(_('Set a manual Pwin before qualifying.'))
            if not rec.client_id:
                raise UserError(_('Set the issuing entity before qualifying.'))
            rec.tender_state = 'qualified'

    def action_set_bid_decision(self):
        for rec in self:
            if rec.tender_state != 'qualified':
                raise UserError(_('Opportunity must be Qualified before entering Bid Decision.'))
            rec.tender_state = 'bid_decision'

    def action_set_no_bid(self):
        self.write({'tender_state': 'no_bid'})

    def action_set_capture(self):
        for rec in self:
            if rec.bid_decision_state != 'approved':
                raise UserError(_('A positive, approved bid decision is required to enter Capture.'))
            rec.tender_state = 'capture'

    def action_set_won(self):
        for rec in self:
            if not rec.tier1_complete:
                raise UserError(_(
                    'Tier 1 (qualification, compliance, site survey, bid decision) must be complete before marking as Won.'
                ))
        return super().action_set_won()

    def _open_related(self, model, name, default_field='opportunity_id'):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _(name),
            'res_model': model,
            'view_mode': 'list,form',
            'domain': [(default_field, '=', self.id)],
            'context': {f'default_{default_field}': self.id},
        }

    def action_view_bid_bonds(self):
        return self._open_related('tender.bid.bond', 'Bid Bonds')

    def action_view_site_surveys(self):
        return self._open_related('tender.site.survey', 'Site Surveys')

    def action_open_capture_plan(self):
        self.ensure_one()
        plan = self.capture_plan_id
        if not plan:
            plan = self.env['tender.capture.plan'].create({
                'opportunity_id': self.id,
                'name': f'Capture Plan — {self.name}',
            })
            self.capture_plan_id = plan.id
        return {
            'type': 'ir.actions.act_window',
            'name': _('Capture Plan'),
            'res_model': 'tender.capture.plan',
            'res_id': plan.id,
            'view_mode': 'form',
        }

    def action_view_risks(self):
        return self._open_related('tender.risk', 'Risk Register')

    def action_view_stakeholders(self):
        return self._open_related('tender.stakeholder', 'Stakeholders')

    def action_view_partner_agreements(self):
        return self._open_related('tender.partner.agreement', 'Partner Agreements')

    def action_view_budget_quotes(self):
        return self._open_related('tender.budget.quote', 'Budget Quotes')

    def action_view_clarifications(self):
        return self._open_related('tender.clarification', 'Clarifications')

    def action_view_prebid_meetings(self):
        return self._open_related('tender.prebid.meeting', 'Pre-Bid Meetings')

    def action_view_bid_team(self):
        return self._open_related('tender.bid.team.member', 'Bid Team')

    def action_view_competitors(self):
        return self._open_related('tender.opportunity.competitor', 'Competitive Landscape')

    def action_view_kickoff_gates(self):
        return self._open_related('tender.kickoff.gate', 'Review Gates')
