# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class ProjectProject(models.Model):
    _inherit = 'project.project'

    # Identification
    buruuj_project_code = fields.Char(string='Project Code', copy=False, tracking=True)
    buruuj_tender_id = fields.Many2one('buruuj.tender', string='Source Tender',
                                        readonly=True, copy=False)

    # Contract data
    buruuj_contract_value = fields.Monetary(string='Contract Value', tracking=True)
    buruuj_baseline_budget = fields.Monetary(string='Baseline Budget',
                                              help='Frozen at award. Used for variance analysis.',
                                              tracking=True)
    buruuj_revised_budget = fields.Monetary(string='Revised Budget',
                                             compute='_compute_revised_budget', store=True)
    buruuj_actual_cost = fields.Monetary(string='Actual Cost',
                                          compute='_compute_actual_cost')
    buruuj_committed_cost = fields.Monetary(string='Committed Cost',
                                             compute='_compute_committed_cost')

    # Schedule
    buruuj_planned_start = fields.Date(string='Planned Start', tracking=True)
    buruuj_planned_end = fields.Date(string='Planned End', tracking=True)
    buruuj_actual_start = fields.Date(string='Actual Start')
    buruuj_actual_end = fields.Date(string='Actual End')
    buruuj_dlp_months = fields.Integer(string='DLP (months)', default=12)
    buruuj_dlp_end = fields.Date(string='DLP End Date',
                                  compute='_compute_dlp_end', store=True)

    # Progress
    buruuj_physical_progress = fields.Float(string='Physical Progress %', tracking=True)
    buruuj_financial_progress = fields.Float(string='Financial Progress %',
                                              compute='_compute_financial_progress')

    # Health
    buruuj_health = fields.Selection([
        ('green', 'Green'),
        ('amber', 'Amber'),
        ('red', 'Red'),
    ], string='Project Health', compute='_compute_health', store=True)

    # Parties
    buruuj_consultant_id = fields.Many2one('res.partner', string='Consultant')
    buruuj_pm_id = fields.Many2one('res.users', string='Project Manager')
    buruuj_qs_id = fields.Many2one('res.users', string='Quantity Surveyor')
    buruuj_site_engineer_id = fields.Many2one('res.users', string='Site Engineer')

    # Geo
    buruuj_site_address = fields.Char(string='Site Address')
    buruuj_site_lat = fields.Float(string='Site Latitude', digits=(10, 6))
    buruuj_site_lng = fields.Float(string='Site Longitude', digits=(10, 6))
    buruuj_geofence_radius = fields.Integer(string='Geofence Radius (m)', default=200)

    # Related
    buruuj_phase_ids = fields.One2many('buruuj.phase', 'project_id', string='Phases')
    buruuj_wbs_ids = fields.One2many('buruuj.wbs', 'project_id', string='WBS')
    buruuj_variation_ids = fields.One2many('buruuj.variation', 'project_id',
                                            string='Variations')
    buruuj_milestone_ids = fields.One2many('buruuj.milestone', 'project_id',
                                            string='Milestones')
    buruuj_risk_ids = fields.One2many('buruuj.risk', 'project_id', string='Risks')
    buruuj_progress_snapshot_ids = fields.One2many(
        'buruuj.progress.snapshot', 'project_id', string='Progress Snapshots')

    # Counts
    buruuj_phase_count = fields.Integer(compute='_compute_counts')
    buruuj_variation_count = fields.Integer(compute='_compute_counts')
    buruuj_milestone_count = fields.Integer(compute='_compute_counts')
    buruuj_risk_count = fields.Integer(compute='_compute_counts')

    @api.depends('buruuj_phase_ids', 'buruuj_variation_ids',
                 'buruuj_milestone_ids', 'buruuj_risk_ids')
    def _compute_counts(self):
        for rec in self:
            rec.buruuj_phase_count = len(rec.buruuj_phase_ids)
            rec.buruuj_variation_count = len(rec.buruuj_variation_ids)
            rec.buruuj_milestone_count = len(rec.buruuj_milestone_ids)
            rec.buruuj_risk_count = len(rec.buruuj_risk_ids)

    @api.depends('buruuj_baseline_budget', 'buruuj_variation_ids.amount',
                 'buruuj_variation_ids.state')
    def _compute_revised_budget(self):
        for rec in self:
            approved = sum(rec.buruuj_variation_ids.filtered(
                lambda v: v.state == 'approved').mapped('amount'))
            rec.buruuj_revised_budget = rec.buruuj_baseline_budget + approved

    def _compute_actual_cost(self):
        # Hook: subcontractor IPCs and procurement actuals plug in here.
        for rec in self:
            rec.buruuj_actual_cost = 0.0

    def _compute_committed_cost(self):
        for rec in self:
            rec.buruuj_committed_cost = 0.0

    @api.depends('buruuj_contract_value', 'buruuj_milestone_ids.amount',
                 'buruuj_milestone_ids.state')
    def _compute_financial_progress(self):
        for rec in self:
            if rec.buruuj_contract_value:
                billed = sum(rec.buruuj_milestone_ids.filtered(
                    lambda m: m.state == 'billed').mapped('amount'))
                rec.buruuj_financial_progress = (
                    100.0 * billed / rec.buruuj_contract_value)
            else:
                rec.buruuj_financial_progress = 0.0

    @api.depends('buruuj_physical_progress', 'buruuj_planned_end',
                 'buruuj_baseline_budget', 'buruuj_actual_cost')
    def _compute_health(self):
        from datetime import date
        for rec in self:
            score = 0
            # Schedule: behind = 1, late = 2
            if rec.buruuj_planned_end and rec.buruuj_planned_end < date.today():
                if rec.buruuj_physical_progress < 100:
                    score += 2
            # Cost overrun
            if (rec.buruuj_baseline_budget
                    and rec.buruuj_actual_cost > rec.buruuj_baseline_budget * 1.05):
                score += 2
            elif (rec.buruuj_baseline_budget
                  and rec.buruuj_actual_cost > rec.buruuj_baseline_budget * 0.95):
                score += 1
            rec.buruuj_health = 'red' if score >= 3 else ('amber' if score >= 1 else 'green')

    # ---- Construction progress (Gantt / S-curve) ----
    def action_view_phase_gantt(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Phase Gantt - %s') % self.name,
            'res_model': 'buruuj.phase',
            'view_mode': 'gantt,list,form',
            'domain': [('project_id', '=', self.id)],
            'context': {'default_project_id': self.id},
        }

    def action_view_wbs_gantt(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('WBS Gantt - %s') % self.name,
            'res_model': 'buruuj.wbs',
            'view_mode': 'gantt,list,form',
            'domain': [('project_id', '=', self.id)],
            'context': {'default_project_id': self.id},
        }

    def action_view_s_curve(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('S-Curve - %s') % self.name,
            'res_model': 'buruuj.progress.snapshot',
            'view_mode': 'graph,list,form',
            'domain': [('project_id', '=', self.id)],
            'context': {'default_project_id': self.id,
                        'search_default_group_by_date': 1},
        }

    def action_capture_progress_snapshot(self):
        self.ensure_one()
        snap = self.env['buruuj.progress.snapshot'].action_capture_from_wbs(
            self.id)
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'buruuj.progress.snapshot',
            'res_id': snap.id,
            'view_mode': 'form',
        }

    @api.depends('buruuj_actual_end', 'buruuj_dlp_months')
    def _compute_dlp_end(self):
        from dateutil.relativedelta import relativedelta
        for rec in self:
            if rec.buruuj_actual_end and rec.buruuj_dlp_months:
                rec.buruuj_dlp_end = rec.buruuj_actual_end + relativedelta(
                    months=rec.buruuj_dlp_months)
            else:
                rec.buruuj_dlp_end = False
