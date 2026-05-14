# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class SiteReport(models.Model):
    """
    Weekly (or daily) site progress report submitted by Site Engineer.
    Captures: physical progress per phase, workforce count, weather,
    issues, photos, and overall progress update.
    Triggers automatic update of phase progress on validation.
    """
    _name = 'salaam.site.report'
    _description = 'Site Progress Report'
    _order = 'report_date desc'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(
        string='Report Reference', required=True, copy=False,
        default=lambda self: _('New'),
    )
    project_id = fields.Many2one(
        'salaam.construction.project', string='Project',
        required=True, ondelete='cascade', index=True,
    )
    report_date = fields.Date(
        string='Report Date', required=True,
        default=fields.Date.today,
    )
    report_period = fields.Selection([
        ('daily',   'Daily'),
        ('weekly',  'Weekly'),
        ('monthly', 'Monthly'),
    ], string='Report Period', default='weekly', required=True)
    state = fields.Selection([
        ('draft',     'Draft'),
        ('submitted', 'Submitted'),
        ('approved',  'Approved'),
    ], string='Status', default='draft', tracking=True)

    submitted_by = fields.Many2one(
        'res.users', string='Submitted By',
        default=lambda self: self.env.user,
    )
    approved_by = fields.Many2one(
        'res.users', string='Approved By', readonly=True,
    )

    # ── SITE CONDITIONS ───────────────────────────────────────────────────────
    weather_condition = fields.Selection([
        ('clear',   'Clear'),
        ('cloudy',  'Cloudy'),
        ('rain',    'Rain'),
        ('dust',    'Dust / Sandstorm'),
        ('extreme', 'Extreme / Work Stopped'),
    ], string='Weather', default='clear')

    workforce_total = fields.Integer(string='Total Workforce on Site')
    workforce_breakdown = fields.Text(
        string='Workforce Breakdown',
        help='e.g. Civil: 45, MEP: 12, Supervisors: 3',
    )
    equipment_on_site = fields.Text(string='Equipment on Site')

    # ── OVERALL PROGRESS ──────────────────────────────────────────────────────
    overall_progress_reported = fields.Float(
        string='Overall Progress Reported (%)', digits=(5, 1), tracking=True,
    )
    previous_progress = fields.Float(
        string='Previous Report Progress (%)', digits=(5, 1), readonly=True,
    )
    progress_this_period = fields.Float(
        string='Progress This Period (%)', compute='_compute_progress_delta',
        digits=(5, 1), store=True,
    )

    # ── PHASE PROGRESS LINES ──────────────────────────────────────────────────
    phase_progress_ids = fields.One2many(
        'salaam.site.report.phase', 'report_id',
        string='Phase Progress',
    )

    # ── NARRATIVE ─────────────────────────────────────────────────────────────
    works_completed = fields.Html(
        string='Works Completed This Period',
    )
    works_planned = fields.Html(
        string='Works Planned Next Period',
    )
    issues_risks = fields.Html(
        string='Issues, Risks & Blockers',
    )
    instructions_received = fields.Text(
        string='Site Instructions / Variation Orders Received',
    )
    health_safety_notes = fields.Text(
        string='Health, Safety & Environment Notes',
    )
    general_notes = fields.Text(string='General Notes')

    # ── ATTACHMENTS handled via chatter ───────────────────────────────────────

    # ── COMPUTED ──────────────────────────────────────────────────────────────
    @api.depends('overall_progress_reported', 'previous_progress')
    def _compute_progress_delta(self):
        for rec in self:
            rec.progress_this_period = (
                rec.overall_progress_reported - (rec.previous_progress or 0)
            )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'salaam.site.report'
                ) or _('New')
        # Auto-capture previous progress
        for vals in vals_list:
            if 'project_id' in vals:
                project = self.env['salaam.construction.project'].browse(
                    vals['project_id']
                )
                vals['previous_progress'] = project.overall_progress
        return super().create(vals_list)

    def action_submit(self):
        self.write({'state': 'submitted'})

    def action_approve(self):
        """Approve and push phase progress updates to project."""
        for rec in self:
            rec.write({
                'state': 'approved',
                'approved_by': self.env.user.id,
            })
            # Update each phase's progress from the report lines
            for line in rec.phase_progress_ids:
                if line.phase_id:
                    line.phase_id.progress = line.progress_reported
            # Update overall project progress
            rec.project_id._compute_overall_progress()
            rec.message_post(
                body=_('Site report approved by %s. Overall progress updated to %s%%.')
                % (self.env.user.name, rec.overall_progress_reported)
            )


class SiteReportPhase(models.Model):
    """Phase-level progress line within a site report."""
    _name = 'salaam.site.report.phase'
    _description = 'Site Report Phase Line'
    _order = 'sequence'

    report_id = fields.Many2one(
        'salaam.site.report', ondelete='cascade', required=True, index=True,
    )
    sequence = fields.Integer(default=10)
    phase_id = fields.Many2one(
        'salaam.construction.phase', string='Phase',
        domain="[('project_id','=',parent.project_id)]",
        required=True,
    )
    phase_type = fields.Selection(
        related='phase_id.phase_type', string='Type',
    )
    progress_previous = fields.Float(
        string='Previous (%)', digits=(5, 1),
        related='phase_id.progress', readonly=True,
    )
    progress_reported = fields.Float(
        string='Progress This Report (%)', digits=(5, 1), required=True,
    )
    progress_delta = fields.Float(
        string='Change (%)', compute='_compute_delta', digits=(5, 1),
    )
    notes = fields.Char(string='Notes')

    @api.depends('progress_reported', 'progress_previous')
    def _compute_delta(self):
        for rec in self:
            rec.progress_delta = rec.progress_reported - (rec.progress_previous or 0)
