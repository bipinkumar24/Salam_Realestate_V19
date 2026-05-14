# -*- coding: utf-8 -*-
from odoo import models, fields, api


class BuruujScorecard(models.Model):
    """Subcontractor performance scorecard (one record per project per period)."""
    _name = 'buruuj.scorecard'
    _description = 'Subcontractor Scorecard'
    _order = 'date desc'

    name = fields.Char(compute='_compute_name', store=True)
    partner_id = fields.Many2one('res.partner', required=True,
                                  domain=[('is_subcontractor', '=', True)])
    project_id = fields.Many2one('project.project')
    subcontract_id = fields.Many2one('buruuj.subcontract')
    date = fields.Date(default=fields.Date.context_today)
    period = fields.Char(string='Period', help='e.g. Q1 2026')

    # 0-5 scores
    quality_score = fields.Float(string='Quality', default=3.0)
    schedule_score = fields.Float(string='Schedule', default=3.0)
    safety_score = fields.Float(string='Safety', default=3.0)
    payment_compliance_score = fields.Float(string='Payment Compliance', default=3.0)
    overall_score = fields.Float(compute='_compute_overall', store=True)

    evaluator_id = fields.Many2one('res.users', default=lambda s: s.env.user)
    notes = fields.Text()

    @api.depends('quality_score', 'schedule_score', 'safety_score',
                 'payment_compliance_score')
    def _compute_overall(self):
        for rec in self:
            rec.overall_score = (
                rec.quality_score + rec.schedule_score
                + rec.safety_score + rec.payment_compliance_score) / 4.0

    @api.depends('partner_id', 'project_id', 'period')
    def _compute_name(self):
        for rec in self:
            parts = [rec.partner_id.name or '', rec.project_id.name or '',
                     rec.period or '']
            rec.name = ' / '.join(p for p in parts if p) or 'Scorecard'
