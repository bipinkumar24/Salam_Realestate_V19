# -*- coding: utf-8 -*-
from odoo import api, fields, models


class TenderSiteSurvey(models.Model):
    _name = 'tender.site.survey'
    _description = 'Site Survey'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'survey_date desc'

    name = fields.Char(required=True, default='New', copy=False, readonly=True)
    opportunity_id = fields.Many2one(
        'crm.lead', string='Opportunity', required=True,
        ondelete='cascade', index=True, tracking=True,
    )
    survey_date = fields.Date(default=fields.Date.context_today, tracking=True)
    team_lead_id = fields.Many2one('res.users', string='Team Lead', tracking=True)
    team_member_ids = fields.Many2many('hr.employee', string='Survey Team')
    location = fields.Char()
    geo_latitude = fields.Float(digits=(10, 7))
    geo_longitude = fields.Float(digits=(10, 7))
    equipment_required = fields.Text(string='Equipment / Permits / Logistics')
    summary_findings = fields.Html(string='Summary Findings')
    exclusions = fields.Text()
    clarifications_needed = fields.Text()
    state = fields.Selection([
        ('planned', 'Planned'),
        ('in_progress', 'In Progress'),
        ('done', 'Completed'),
        ('waived', 'Waived'),
    ], default='planned', tracking=True)
    waiver_reason = fields.Text()
    line_ids = fields.One2many('tender.site.survey.line', 'survey_id', string='Findings')
    line_count = fields.Integer(compute='_compute_line_count')
    risk_count = fields.Integer(compute='_compute_line_count')
    boq_discrepancy_count = fields.Integer(compute='_compute_line_count')
    report_attachment_ids = fields.Many2many(
        'ir.attachment', 'tender_survey_report_rel',
        'survey_id', 'attachment_id', string='Report Attachments',
    )
    company_id = fields.Many2one(
        'res.company', related='opportunity_id.company_id',
        store=True, readonly=True,
    )

    @api.depends('line_ids', 'line_ids.has_risk', 'line_ids.boq_discrepancy')
    def _compute_line_count(self):
        for rec in self:
            rec.line_count = len(rec.line_ids)
            rec.risk_count = len(rec.line_ids.filtered('has_risk'))
            rec.boq_discrepancy_count = len(rec.line_ids.filtered('boq_discrepancy'))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('tender.site.survey') or 'SS/0001'
        return super().create(vals_list)

    def action_start(self):
        self.write({'state': 'in_progress'})

    def action_complete(self):
        self.write({'state': 'done'})

    def action_waive(self):
        self.write({'state': 'waived'})


class TenderSiteSurveyLine(models.Model):
    _name = 'tender.site.survey.line'
    _description = 'Site Survey Finding'
    _order = 'sequence, id'

    sequence = fields.Integer(default=10)
    survey_id = fields.Many2one(
        'tender.site.survey', required=True, ondelete='cascade', index=True,
    )
    opportunity_id = fields.Many2one(
        related='survey_id.opportunity_id', store=True, index=True,
    )
    category = fields.Selection([
        ('utility', 'Utility / Services'),
        ('soil', 'Soil / Geotechnical'),
        ('access', 'Access / Logistics'),
        ('market', 'Market / Resources'),
        ('regulatory', 'Regulatory / Permits'),
        ('environmental', 'Environmental'),
        ('safety', 'Safety / Security'),
        ('other', 'Other'),
    ], required=True, default='other')
    observation = fields.Text(required=True)
    photo_attachment_ids = fields.Many2many(
        'ir.attachment', 'tender_survey_line_photo_rel',
        'line_id', 'attachment_id', string='Photos',
    )
    has_risk = fields.Boolean(string='Risk Identified')
    risk_id = fields.Many2one('tender.risk', string='Linked Risk', ondelete='set null')
    boq_discrepancy = fields.Boolean(string='BoQ Discrepancy')
    boq_notes = fields.Text(string='BoQ Notes')
    voice_note_attachment_id = fields.Many2one(
        'ir.attachment', string='Voice Note',
    )
