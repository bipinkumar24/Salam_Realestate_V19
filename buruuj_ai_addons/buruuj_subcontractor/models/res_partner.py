# -*- coding: utf-8 -*-
from odoo import models, fields, api


class ResPartner(models.Model):
    _inherit = 'res.partner'

    subcontract_ids = fields.One2many('buruuj.subcontract', 'partner_id')
    subcontract_count = fields.Integer(compute='_compute_subcontract_count')
    scorecard_ids = fields.One2many('buruuj.scorecard', 'partner_id')

    def _compute_subcontract_count(self):
        for rec in self:
            rec.subcontract_count = len(rec.subcontract_ids)

    @api.depends('scorecard_ids.overall_score')
    def _compute_performance_score(self):
        for rec in self:
            scores = rec.scorecard_ids.mapped('overall_score')
            rec.performance_score = sum(scores) / len(scores) if scores else 0.0

    performance_score = fields.Float(
        compute='_compute_performance_score', store=True,
        help='Average overall score from all scorecards.')
