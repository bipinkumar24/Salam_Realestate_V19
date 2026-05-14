# -*- coding: utf-8 -*-
from odoo import api, fields, models


class TenderComplianceMatrix(models.Model):
    _name = 'tender.compliance.matrix'
    _description = 'Tender Compliance Matrix'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(required=True, default='Compliance Matrix', tracking=True)
    opportunity_id = fields.Many2one(
        'crm.lead', string='Opportunity', required=True,
        ondelete='cascade', index=True, tracking=True,
    )
    line_ids = fields.One2many(
        'tender.compliance.matrix.line', 'matrix_id', string='Requirements',
    )
    line_count = fields.Integer(compute='_compute_progress', store=True)
    compliant_count = fields.Integer(compute='_compute_progress', store=True)
    progress = fields.Float(
        string='Compliance %', compute='_compute_progress', store=True,
        help='Percentage of requirements marked Compliant.',
    )
    state = fields.Selection([
        ('draft', 'Draft'),
        ('in_progress', 'In Progress'),
        ('complete', 'Complete'),
    ], default='draft', tracking=True, compute='_compute_state', store=True)
    company_id = fields.Many2one(
        'res.company', related='opportunity_id.company_id',
        store=True, readonly=True,
    )

    @api.depends('line_ids', 'line_ids.status')
    def _compute_progress(self):
        for rec in self:
            total = len(rec.line_ids)
            compliant = len(rec.line_ids.filtered(lambda l: l.status == 'compliant'))
            rec.line_count = total
            rec.compliant_count = compliant
            rec.progress = (compliant / total * 100.0) if total else 0.0

    @api.depends('line_ids.status', 'progress')
    def _compute_state(self):
        for rec in self:
            if not rec.line_ids:
                rec.state = 'draft'
            elif rec.progress >= 100.0:
                rec.state = 'complete'
            else:
                rec.state = 'in_progress'


class TenderComplianceMatrixLine(models.Model):
    _name = 'tender.compliance.matrix.line'
    _description = 'Compliance Matrix Line'
    _order = 'sequence, id'

    sequence = fields.Integer(default=10)
    matrix_id = fields.Many2one(
        'tender.compliance.matrix', required=True, ondelete='cascade', index=True,
    )
    opportunity_id = fields.Many2one(
        related='matrix_id.opportunity_id', store=True, index=True,
    )
    requirement = fields.Text(string='Requirement', required=True)
    source_clause = fields.Char(string='RFP Clause Reference')
    response_owner_id = fields.Many2one('res.users', string='Owner')
    status = fields.Selection([
        ('pending', 'Pending'),
        ('in_progress', 'In Progress'),
        ('compliant', 'Compliant'),
        ('non_compliant', 'Non-Compliant'),
        ('not_applicable', 'Not Applicable'),
    ], default='pending', required=True)
    response_text = fields.Text(string='Response')
    is_showstopper = fields.Boolean(
        string='Showstopper',
        help='Non-compliance disqualifies the bid.',
    )
    evidence_attachment_ids = fields.Many2many(
        'ir.attachment', 'tender_matrix_line_attachment_rel',
        'line_id', 'attachment_id', string='Evidence',
    )
