# -*- coding: utf-8 -*-
"""Add an action on Subcontract to recommend the best partner.

Pulls scorecard history, current workload, and license validity from the
existing data, and asks Claude to rank top 3 with a short justification."""
import json
import logging
import re
from datetime import date, timedelta
from odoo import models, fields, api, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


SUB_SYSTEM_PROMPT = """You are a Procurement Manager at Buruuj Construction Co. \
You will be given a JSON list of available subcontractors with their \
performance history, current workload, and credential status. Your job is to \
recommend the top 3 candidates for a specific scope of work.

You must output ONLY valid JSON in the following exact schema, with no \
preamble, no markdown fences, no commentary:

{
  "recommendations": [
    {
      "partner_id": <integer, the partner_id from the input>,
      "rank": 1,
      "score": 0.0,
      "rationale": "Plain-English justification, 1-2 sentences. Cite specific \
data points like average score, recent NCRs, current contract count, or \
license expiry."
    }
  ],
  "general_notes": "Any cross-cutting observations about the candidate pool. \
For example, if all subcontractors with valid licenses have heavy current \
workload, flag that here."
}

Scoring guide (0-10):
- Performance score average: weight 40%
- Current workload (lower is better, prefer those with 0-1 active contracts): \
weight 25%
- License/insurance validity (must be valid; near-expiry is a negative): \
weight 20%
- Trade specialisation match: weight 15%

Only include partners with valid trade licenses. If a partner has an expired \
or missing license, do NOT recommend them — note this in general_notes.

Return between 1 and 3 recommendations. Fewer is fine if there are not enough \
qualified candidates.
"""


class BuruujSubcontract(models.Model):
    _inherit = 'buruuj.subcontract'

    ai_recommendation_text = fields.Html(
        string='AI Recommendation', readonly=True,
        help='AI-generated subcontractor recommendation. For reference only.')
    ai_last_task_id = fields.Many2one(
        'buruuj.ai.task', string='Last AI Task', readonly=True)

    def action_ai_recommend_subcontractor(self):
        """Build a candidate list and ask Claude to rank them."""
        self.ensure_one()
        if not self.env['buruuj.ai.client'].is_enabled():
            raise UserError(_(
                "AI is not configured. Ask your administrator to set the "
                "Anthropic API key in Settings."))
        if self.state != 'draft':
            raise UserError(_(
                "Recommendations are only meaningful on a Draft subcontract."))
        if not self.trade_id:
            raise UserError(_(
                "Please pick a Trade first — the AI uses it to filter candidates."))

        # Build candidate pool: active subcontractors with at least one matching trade
        Partner = self.env['res.partner']
        candidates = Partner.search([
            ('is_subcontractor', '=', True),
            ('active', '=', True),
            ('trade_ids', 'in', self.trade_id.id),
        ])

        if not candidates:
            raise UserError(_(
                "No subcontractors with the trade '%s' are registered.") % self.trade_id.name)

        # Build candidate data
        today = date.today()
        candidate_data = []
        for partner in candidates:
            scorecards = self.env['buruuj.scorecard'].search(
                [('partner_id', '=', partner.id)], order='date desc', limit=10)
            active_subs = self.env['buruuj.subcontract'].search_count([
                ('partner_id', '=', partner.id),
                ('state', 'in', ['signed', 'in_progress']),
            ])

            license_status = 'unknown'
            if partner.trade_license_expiry:
                days_left = (partner.trade_license_expiry - today).days
                if days_left < 0:
                    license_status = 'EXPIRED'
                elif days_left < 30:
                    license_status = f'expiring in {days_left} days'
                else:
                    license_status = f'valid ({days_left} days remaining)'
            else:
                license_status = 'NOT RECORDED'

            insurance_status = 'unknown'
            if partner.insurance_expiry:
                days_left = (partner.insurance_expiry - today).days
                if days_left < 0:
                    insurance_status = 'EXPIRED'
                else:
                    insurance_status = f'valid ({days_left} days remaining)'
            else:
                insurance_status = 'NOT RECORDED'

            candidate_data.append({
                'partner_id': partner.id,
                'name': partner.name,
                'trades': [t.code for t in partner.trade_ids],
                'overall_performance_score': round(partner.performance_score or 0.0, 2),
                'recent_scorecards': [{
                    'period': sc.period or '',
                    'overall': round(sc.overall_score or 0.0, 2),
                    'quality': round(sc.quality_score or 0.0, 2),
                    'schedule': round(sc.schedule_score or 0.0, 2),
                    'safety': round(sc.safety_score or 0.0, 2),
                    'payment': round(sc.payment_compliance_score or 0.0, 2),
                } for sc in scorecards[:5]],
                'active_subcontract_count': active_subs,
                'trade_license_status': license_status,
                'insurance_status': insurance_status,
            })

        # Build the prompt
        client = self.env['buruuj.ai.client']
        scope_summary = (self.title or '') + " — " + (self.scope_of_work or '')[:1000]
        user_msg = (
            f"Scope to be subcontracted: {scope_summary}\n"
            f"Required trade: {self.trade_id.name} (code: {self.trade_id.code})\n"
            f"Estimated contract value: {self.contract_value} {self.currency_id.name}\n"
            f"Project: {self.project_id.name}\n\n"
            f"Candidates:\n{json.dumps(candidate_data, indent=2)}"
        )

        result = client.complete(
            system=SUB_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_msg}],
            max_tokens=2048,
            task_type='sub_recommend',
            task_record=('buruuj.subcontract', self.id),
        )

        text = result['text'].strip()
        text = re.sub(r'^```(?:json)?\s*', '', text)
        text = re.sub(r'\s*```\s*$', '', text)

        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            _logger.error("AI returned non-JSON: %s", text[:500])
            raise UserError(_(
                "AI response was not valid JSON. Check AI Tasks for the raw "
                "response."))

        # Build readable HTML
        recs = parsed.get('recommendations', [])
        html_parts = ['<div>']
        if recs:
            html_parts.append('<h4 style="color:#0B2545;">AI Recommendations</h4><ol>')
            for rec in recs:
                pid = rec.get('partner_id')
                partner = Partner.browse(pid) if pid else False
                pname = partner.name if partner and partner.exists() else 'Unknown'
                score = rec.get('score', 0)
                rationale = rec.get('rationale', '')
                html_parts.append(
                    f'<li><strong>{pname}</strong> '
                    f'(score: {score}/10)<br/>'
                    f'<em>{rationale}</em></li>')
            html_parts.append('</ol>')
        general = parsed.get('general_notes', '')
        if general:
            html_parts.append(
                f'<p><strong>General notes:</strong> {general}</p>')
        html_parts.append(
            '<p style="color:#888;font-size:0.9em;">'
            'AI recommendation for reference only. Final selection is the PM\'s '
            'decision and should consider current commercial offers.</p></div>')

        self.write({
            'ai_recommendation_text': ''.join(html_parts),
            'ai_last_task_id': result['task_id'],
        })
        self.message_post(body=_(
            "AI subcontractor recommendation generated. See the AI Recommendation "
            "field on the subcontract form."))

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Recommendation Ready'),
                'message': _('Reviewed %d candidate(s); top %d shown on the form.')
                            % (len(candidate_data), len(recs)),
                'type': 'success',
                'sticky': False,
            },
        }
