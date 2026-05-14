# -*- coding: utf-8 -*-
"""AI task log — every call is recorded for audit and cost monitoring."""
from odoo import models, fields, api


class BuruujAITask(models.Model):
    _name = 'buruuj.ai.task'
    _description = 'AI Task Log'
    _order = 'create_date desc'

    name = fields.Char(compute='_compute_name', store=True)
    task_type = fields.Selection([
        ('boq_draft', 'BOQ Draft from Drawings'),
        ('ncr_draft', 'NCR Draft from Photo'),
        ('sub_recommend', 'Subcontractor Recommendation'),
        ('vo_draft', 'Variation Order Draft'),
        ('generic', 'Generic'),
    ], required=True, default='generic')

    state = fields.Selection([
        ('running', 'Running'),
        ('done', 'Done'),
        ('failed', 'Failed'),
    ], default='running', required=True)

    model = fields.Char(string='Claude Model')
    user_id = fields.Many2one(
        'res.users', default=lambda self: self.env.user, readonly=True)

    system_prompt = fields.Text(string='System Prompt')
    response_text = fields.Text(string='Response')
    error_message = fields.Text()

    input_tokens = fields.Integer()
    output_tokens = fields.Integer()
    estimated_cost_usd = fields.Float(
        string='Estimated Cost (USD)',
        compute='_compute_cost', store=True,
        help='Rough estimate based on Claude Opus pricing. Actual billing on Anthropic console.')

    # Optional reference back to the source record
    ref_model = fields.Char(string='Source Model')
    ref_id = fields.Integer(string='Source ID')
    ref_display = fields.Char(string='Source', compute='_compute_ref_display')

    company_id = fields.Many2one(
        'res.company', default=lambda self: self.env.company, readonly=True)

    # Indicative pricing as of model release. NOT authoritative — the Anthropic
    # console is. We use this for ballpark cost monitoring only.
    INPUT_COST_PER_MTOK = 15.0   # USD per 1M input tokens (Opus indicative)
    OUTPUT_COST_PER_MTOK = 75.0  # USD per 1M output tokens

    @api.depends('task_type', 'create_date', 'state')
    def _compute_name(self):
        for rec in self:
            label = dict(rec._fields['task_type'].selection).get(
                rec.task_type, rec.task_type)
            rec.name = f"{label} - {rec.create_date or ''}"

    @api.depends('input_tokens', 'output_tokens')
    def _compute_cost(self):
        for rec in self:
            rec.estimated_cost_usd = (
                (rec.input_tokens / 1_000_000.0) * rec.INPUT_COST_PER_MTOK
                + (rec.output_tokens / 1_000_000.0) * rec.OUTPUT_COST_PER_MTOK
            )

    @api.depends('ref_model', 'ref_id')
    def _compute_ref_display(self):
        for rec in self:
            if rec.ref_model and rec.ref_id:
                try:
                    record = self.env[rec.ref_model].browse(rec.ref_id)
                    rec.ref_display = (record.display_name
                                       if record.exists() else f"{rec.ref_model}#{rec.ref_id}")
                except Exception:
                    rec.ref_display = f"{rec.ref_model}#{rec.ref_id}"
            else:
                rec.ref_display = ''

    def action_open_source(self):
        """Open the source record this task was linked to."""
        self.ensure_one()
        if not (self.ref_model and self.ref_id):
            return False
        return {
            'type': 'ir.actions.act_window',
            'res_model': self.ref_model,
            'res_id': self.ref_id,
            'view_mode': 'form',
            'target': 'current',
        }

    @api.model
    def cron_clean_ai_tasks(self):
        """Weekly cleanup of done AI tasks older than 90 days."""
        from datetime import timedelta
        cutoff = fields.Datetime.now() - timedelta(days=90)
        old_tasks = self.search([
            ('create_date', '<', cutoff),
            ('state', '=', 'done'),
        ])
        old_tasks.unlink()
        return True
