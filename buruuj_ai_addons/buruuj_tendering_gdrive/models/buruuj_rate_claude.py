# -*- coding: utf-8 -*-
import json
import logging
import re

from odoo import api, fields, models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

CLAUDE_MODEL = 'claude-sonnet-4-6'

REGION_HINTS = {
    'DJ': 'Djibouti (DJF, French construction codes, hot arid climate)',
    'KE': 'Kenya (KES, BS-influenced standards, mixed urban/rural)',
    'UG': 'Uganda (UGX, BS-influenced standards)',
    'CD': 'DR Congo (CDF / USD, French and Belgian influences)',
    'SO': 'Somalia (USD denominated, limited formal supply chain)',
    'AE': 'United Arab Emirates (AED, Gulf-region standards, premium materials)',
    'OTHER': 'generic East-African / MENA construction context',
}

SYSTEM_PROMPT = """You are a senior construction quantity surveyor preparing a master-rate catalogue.
You will be asked to generate a list of master-rate items for a given trade, category, and region.
Return ONLY a JSON array (no commentary, no markdown fences) of objects with this exact schema:

[
  {
    "code": "<short uppercase identifier, e.g. CONC-001>",
    "name": "<descriptive item name, one line>",
    "category": "<one of: labor, material, equipment, subcontractor, composite>",
    "uom": "<one of: Units, kg, m, m², m³, l, h, day>",
    "unit_rate": <numeric>,
    "notes": "<optional one-line note about scope or assumptions>"
  }
]

Rules:
- Codes must be unique within the response. Use a short trade prefix (3-5 letters) + sequence.
- Unit rates must be realistic for the stated region in the local currency assumed by the user.
- "category" MUST exactly match one of the allowed values.
- "uom" MUST exactly match one of the allowed values.
- Do not include trailing commas. Do not wrap the JSON in code fences. Do not add commentary."""


class BuruujRateClaudeGenerate(models.TransientModel):
    _name = 'buruuj.rate.claude.generate'
    _description = 'Generate Master Rates with Claude'

    trade_id = fields.Many2one('buruuj.trade', string='Trade')
    category = fields.Selection([
        ('labor', 'Labor'),
        ('material', 'Material'),
        ('equipment', 'Equipment'),
        ('subcontractor', 'Subcontractor'),
        ('composite', 'Composite Rate'),
    ], string='Category', default='composite', required=True)
    region = fields.Selection([
        ('DJ', 'Djibouti'),
        ('KE', 'Kenya'),
        ('UG', 'Uganda'),
        ('CD', 'DR Congo'),
        ('SO', 'Somalia'),
        ('AE', 'United Arab Emirates'),
        ('OTHER', 'Other / Generic'),
    ], string='Region', default='DJ', required=True)
    item_count = fields.Integer(string='Number of items', default=20)
    extra_context = fields.Text(
        string='Extra context',
        help='Optional notes to steer Claude — e.g. "Q3 2026 prices", "high-rise concrete works".')
    result_summary = fields.Text(string='Result', readonly=True)

    @api.constrains('item_count')
    def _check_item_count(self):
        for rec in self:
            if rec.item_count and (rec.item_count < 1 or rec.item_count > 50):
                raise UserError(_('Number of items must be between 1 and 50.'))

    def action_generate(self):
        self.ensure_one()
        items = self._call_claude()
        created = self._upsert_items(items)
        return {
            'type': 'ir.actions.act_window',
            'name': _('Claude-generated drafts (%d)') % len(created),
            'res_model': 'buruuj.rate',
            'view_mode': 'list,form',
            'views': [(False, 'list'), (False, 'form')],
            'domain': [('id', 'in', created.ids)],
            'target': 'current',
            'context': {'search_default_active_test': 0, 'active_test': False},
        }

    def _call_claude(self):
        try:
            import anthropic
        except ImportError:
            raise UserError(_(
                'Python package "anthropic" not installed.\n'
                'Run: "%s" -m pip install anthropic\n'
                'Then restart Odoo.'
            ) % __import__('sys').executable)

        cp = self.env['ir.config_parameter'].sudo()
        api_key = cp.get_param('buruuj_tendering_gdrive.anthropic_api_key')
        if not api_key:
            raise UserError(_('Anthropic API key not configured. '
                              'Open "Drive Setup" on Master Rates and paste the key.'))

        trade_label = self.trade_id.name or 'general construction'
        region_hint = REGION_HINTS.get(self.region, REGION_HINTS['OTHER'])
        n = self.item_count or 20

        user_prompt = (
            f"Trade: {trade_label}\n"
            f"Category: {self.category}\n"
            f"Region: {region_hint}\n"
            f"Generate exactly {n} master-rate items.\n"
        )
        if self.extra_context:
            user_prompt += f"Additional context: {self.extra_context}\n"
        user_prompt += "\nReturn the JSON array now."

        client = anthropic.Anthropic(api_key=api_key)
        try:
            response = client.messages.create(
                model=CLAUDE_MODEL,
                max_tokens=8000,
                system=SYSTEM_PROMPT,
                messages=[{'role': 'user', 'content': user_prompt}],
            )
        except Exception as e:
            raise UserError(_('Claude API call failed: %s') % e)

        text = ''.join(b.text for b in response.content if getattr(b, 'type', '') == 'text')
        items = self._parse_json_array(text)
        if not items:
            raise UserError(_(
                'Claude returned no parseable items.\n\n--- raw response ---\n%s'
            ) % text[:2000])
        return items

    @staticmethod
    def _parse_json_array(text):
        text = text.strip()
        # Strip accidental code fences if Claude added them.
        text = re.sub(r'^```(?:json)?\s*', '', text)
        text = re.sub(r'\s*```$', '', text)
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            # Fallback: extract the first JSON array in the text.
            m = re.search(r'\[.*\]', text, re.DOTALL)
            if not m:
                return []
            try:
                data = json.loads(m.group(0))
            except json.JSONDecodeError:
                return []
        return data if isinstance(data, list) else []

    def _resolve_uom(self, uom_label):
        if not uom_label:
            return self.env.ref('uom.product_uom_unit', raise_if_not_found=False)
        Uom = self.env['uom.uom']
        # Common aliases the model returns -> canonical Odoo UOM names
        aliases = {
            'm³': ['m³', 'm3', 'Cubic Meter(s)', 'Cubic Meter'],
            'm²': ['m²', 'm2', 'Square Meter(s)', 'Square Meter'],
            'm':  ['m', 'Meter(s)', 'Meter'],
            'kg': ['kg', 'kg(s)', 'Kilogram(s)', 'Kilogram', 'kgs'],
            'l':  ['l', 'L', 'Liter(s)', 'Litre(s)', 'Liter'],
            'h':  ['h', 'Hour(s)', 'Hour'],
            'day': ['day', 'Day(s)', 'Days'],
            'Units': ['Units', 'Unit(s)', 'Unit', 'pcs', 'Each'],
        }
        candidates = aliases.get(uom_label, [uom_label])
        for c in candidates:
            uom = Uom.search([('name', '=', c)], limit=1)
            if uom:
                return uom
        return self.env.ref('uom.product_uom_unit', raise_if_not_found=False)

    def _unique_code(self, base_code, existing_codes):
        code = (base_code or 'AI').strip().upper()[:32] or 'AI'
        if code not in existing_codes:
            return code
        i = 2
        while f'{code}-{i}' in existing_codes:
            i += 1
        return f'{code}-{i}'

    def _upsert_items(self, items):
        Rate = self.env['buruuj.rate']
        company = self.env.company
        existing = set(
            Rate.with_context(active_test=False)
                .search([('company_id', '=', company.id)])
                .mapped('code')
        )
        unit_fallback = self.env.ref('uom.product_uom_unit', raise_if_not_found=False)
        created = Rate
        for it in items:
            if not isinstance(it, dict):
                continue
            code = self._unique_code(it.get('code'), existing)
            existing.add(code)
            uom = self._resolve_uom(it.get('uom'))
            if not uom:
                uom = unit_fallback
            cat = it.get('category') or self.category
            if cat not in ('labor', 'material', 'equipment', 'subcontractor', 'composite'):
                cat = self.category
            try:
                unit_rate = float(it.get('unit_rate') or 0.0)
            except (TypeError, ValueError):
                unit_rate = 0.0
            note = (it.get('notes') or '').strip()
            ai_tag = '[Claude draft] '
            vals = {
                'code': code,
                'name': (it.get('name') or 'Untitled').strip()[:512],
                'category': cat,
                'uom_id': uom.id if uom else False,
                'unit_rate': unit_rate,
                'trade_id': self.trade_id.id or False,
                'company_id': company.id,
                'active': False,
                'notes': ai_tag + note if note else ai_tag.strip(),
            }
            try:
                created |= Rate.create(vals)
            except Exception as e:
                _logger.warning('Skipping AI item %s: %s', code, e)
                continue
        return created
