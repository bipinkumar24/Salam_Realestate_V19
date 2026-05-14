# -*- coding: utf-8 -*-
"""Add AI drafting button to Variation Orders.

Given a client change request (free text or pasted email), Claude drafts the
VO description, estimated cost impact range, time impact, and contractual
basis."""
import json
import logging
import re
from odoo import models, fields, api, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


VO_SYSTEM_PROMPT = """You are a senior Quantity Surveyor at Buruuj Construction Co. \
You will be given a client change request (in any format — email, memo, verbal \
notes). Your job is to draft a Variation Order (VO).

You must output ONLY valid JSON in the following exact schema, with no \
preamble, no markdown fences, no commentary:

{
  "title": "Short title for the VO, max 100 characters",
  "initiated_by": "client" | "consultant" | "contractor",
  "description_html": "Clean HTML describing the change. Use <p>, <ul>, <li>. \
Identify what is being added, modified, or removed",
  "cost_impact_low": 0.0,
  "cost_impact_high": 0.0,
  "cost_basis": "How the cost range was estimated. Be honest if speculative.",
  "time_impact_days_low": 0,
  "time_impact_days_high": 0,
  "time_basis": "How the time impact was estimated.",
  "contractual_questions": [
    "List 1-3 questions to clarify with the client/consultant before formal submission"
  ]
}

Important:
- Cost ranges should be conservative. If you cannot estimate, return 0 for \
  both low and high and explain in cost_basis.
- Do NOT invent specific figures. The QS will price properly. Your role is to \
  identify the magnitude (small / medium / large) and surface unknowns.
- Always include contractual_questions — almost every VO has at least one.
"""


class BuruujVariation(models.Model):
    _inherit = 'buruuj.variation'

    ai_source_request = fields.Html(
        string='Client Change Request (Source)',
        help='Paste the client email, memo, or notes describing the requested '
             'change. Click \'Draft from Request\' to have AI pre-fill the VO.')
    ai_cost_low = fields.Monetary(
        string='AI Cost Estimate (Low)',
        readonly=True, currency_field='currency_id')
    ai_cost_high = fields.Monetary(
        string='AI Cost Estimate (High)',
        readonly=True, currency_field='currency_id')
    ai_time_low = fields.Integer(string='AI Time Estimate Low (days)', readonly=True)
    ai_time_high = fields.Integer(string='AI Time Estimate High (days)', readonly=True)
    ai_cost_basis = fields.Text(string='AI Cost Basis', readonly=True)
    ai_time_basis = fields.Text(string='AI Time Basis', readonly=True)
    ai_contractual_questions = fields.Html(
        string='AI Suggested Questions', readonly=True)
    ai_last_task_id = fields.Many2one(
        'buruuj.ai.task', string='Last AI Task', readonly=True)

    def action_ai_draft_vo(self):
        """Send the source request to Claude and pre-fill the VO."""
        self.ensure_one()
        if not self.env['buruuj.ai.client'].is_enabled():
            raise UserError(_(
                "AI is not configured. Ask your administrator to set the "
                "Anthropic API key in Settings."))
        if not self.ai_source_request:
            raise UserError(_(
                "Please paste the client change request in the source field first."))
        if self.state != 'draft':
            raise UserError(_(
                "AI drafting is only available on a Draft VO."))

        # Strip HTML to plain text for the prompt
        from odoo.tools import html2plaintext
        source_text = html2plaintext(self.ai_source_request)

        client = self.env['buruuj.ai.client']
        context = (
            f"Project: {self.project_id.name or 'Unspecified'}\n"
            f"Project contract value: {self.project_id.buruuj_contract_value or 'Unknown'} "
            f"{self.currency_id.name}\n\n"
            f"Client change request:\n{source_text}"
        )

        result = client.complete(
            system=VO_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": context}],
            max_tokens=2048,
            task_type='vo_draft',
            task_record=('buruuj.variation', self.id),
        )

        text = result['text'].strip()
        text = re.sub(r'^```(?:json)?\s*', '', text)
        text = re.sub(r'\s*```\s*$', '', text)

        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            _logger.error("AI returned non-JSON: %s", text[:500])
            raise UserError(_(
                "AI response was not valid JSON. Check AI Tasks for details."))

        # Apply, never overwrite user-set fields
        updates = {'ai_last_task_id': result['task_id']}
        if not self.title and parsed.get('title'):
            updates['title'] = parsed['title'][:200]
        if parsed.get('initiated_by') in ('client', 'consultant', 'contractor'):
            if not self.initiated_by or self.initiated_by == 'client':
                updates['initiated_by'] = parsed['initiated_by']
        if not self.description and parsed.get('description_html'):
            updates['description'] = parsed['description_html']

        # AI fields (always set)
        updates['ai_cost_low'] = float(parsed.get('cost_impact_low') or 0.0)
        updates['ai_cost_high'] = float(parsed.get('cost_impact_high') or 0.0)
        updates['ai_time_low'] = int(parsed.get('time_impact_days_low') or 0)
        updates['ai_time_high'] = int(parsed.get('time_impact_days_high') or 0)
        updates['ai_cost_basis'] = parsed.get('cost_basis', '')
        updates['ai_time_basis'] = parsed.get('time_basis', '')

        questions = parsed.get('contractual_questions', [])
        if questions:
            updates['ai_contractual_questions'] = (
                '<ul>' + ''.join(f'<li>{q}</li>' for q in questions) + '</ul>')

        self.write(updates)
        self.message_post(body=_(
            "AI drafted this VO. Review carefully — the QS must price the "
            "variation properly before submission to the client."))

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('VO Drafted'),
                'message': _('Cost range: %.0f - %.0f. Time range: %d - %d days.')
                            % (updates['ai_cost_low'], updates['ai_cost_high'],
                               updates['ai_time_low'], updates['ai_time_high']),
                'type': 'success',
                'sticky': False,
            },
        }
