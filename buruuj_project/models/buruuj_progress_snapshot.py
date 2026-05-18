# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class BuruujProgressSnapshot(models.Model):
    """Periodic project progress snapshot used to draw the S-curve.

    One row per project per reporting date. The graph view plots
    planned vs earned cumulative % over time.
    """
    _name = 'buruuj.progress.snapshot'
    _description = 'Project Progress Snapshot (S-curve point)'
    _order = 'project_id, snapshot_date'
    _rec_name = 'snapshot_date'

    project_id = fields.Many2one('project.project', required=True,
                                  ondelete='cascade', index=True)
    snapshot_date = fields.Date(required=True, default=fields.Date.context_today)
    period_label = fields.Char(
        string='Period', help='Optional label, e.g. "Week 12" or "Mar-2026".')

    planned_progress = fields.Float(
        string='Planned Cumulative %',
        help='Baseline cumulative % planned to be complete by this date.')
    earned_progress = fields.Float(
        string='Earned Cumulative %',
        help='Cumulative % actually earned (physical progress) by this date.')

    planned_cumulative_cost = fields.Monetary(string='Planned Cumulative Cost')
    actual_cumulative_cost = fields.Monetary(string='Actual Cumulative Cost')

    schedule_variance = fields.Float(
        string='SV %', compute='_compute_variances', store=True,
        help='Earned - Planned. Negative = behind schedule.')
    cost_variance = fields.Monetary(
        string='CV', compute='_compute_variances', store=True,
        help='Planned cost - Actual cost. Negative = over budget.')

    notes = fields.Char()
    currency_id = fields.Many2one(
        'res.currency', default=lambda s: s.env.company.currency_id)
    company_id = fields.Many2one(
        'res.company', default=lambda s: s.env.company)

    _sql_constraints = [
        ('uniq_project_date', 'unique(project_id, snapshot_date)',
         'Only one progress snapshot per project per date.'),
    ]

    @api.depends('planned_progress', 'earned_progress',
                 'planned_cumulative_cost', 'actual_cumulative_cost')
    def _compute_variances(self):
        for rec in self:
            rec.schedule_variance = rec.earned_progress - rec.planned_progress
            rec.cost_variance = (rec.planned_cumulative_cost
                                  - rec.actual_cumulative_cost)

    @api.constrains('planned_progress', 'earned_progress')
    def _check_percent_range(self):
        for rec in self:
            for value in (rec.planned_progress, rec.earned_progress):
                if value < 0 or value > 100:
                    raise UserError(_('Progress % must be between 0 and 100.'))

    @api.model
    def action_capture_from_wbs(self, project_id):
        """Helper: build a snapshot for today from current WBS state.

        Planned % is the cost-weighted planned position computed from
        WBS planned_start / planned_end vs today. Earned % is the
        cost-weighted actual progress.
        """
        today = fields.Date.context_today(self)
        wbs_lines = self.env['buruuj.wbs'].search([
            ('project_id', '=', project_id),
        ])
        total_planned_cost = sum(wbs_lines.mapped('planned_cost')) or 0.0
        if not total_planned_cost:
            raise UserError(_(
                'Cannot capture snapshot: no WBS with planned cost on '
                'this project.'))
        planned_weighted = 0.0
        earned_weighted = 0.0
        for wbs in wbs_lines:
            weight = (wbs.planned_cost / total_planned_cost) * 100.0
            # Time-based planned % for this WBS
            if wbs.planned_start and wbs.planned_end and wbs.planned_end > wbs.planned_start:
                if today <= wbs.planned_start:
                    pct = 0.0
                elif today >= wbs.planned_end:
                    pct = 100.0
                else:
                    span = (wbs.planned_end - wbs.planned_start).days
                    elapsed = (today - wbs.planned_start).days
                    pct = 100.0 * elapsed / span
            else:
                pct = 0.0
            planned_weighted += weight * pct / 100.0
            earned_weighted += weight * wbs.progress / 100.0
        actual_cost = sum(wbs_lines.mapped('actual_cost'))
        return self.create({
            'project_id': project_id,
            'snapshot_date': today,
            'planned_progress': planned_weighted,
            'earned_progress': earned_weighted,
            'planned_cumulative_cost': total_planned_cost,
            'actual_cumulative_cost': actual_cost,
        })
