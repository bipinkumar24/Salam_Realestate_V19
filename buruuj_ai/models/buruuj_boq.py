# -*- coding: utf-8 -*-
"""Add AI drafting button to the BOQ.

When the user uploads a tender drawing/spec PDF and clicks "Draft from Drawings",
Claude reads the document and produces a structured BOQ with sections and lines,
matched against the master rate database where possible."""
import json
import logging
import re
from odoo import models, fields, api, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


BOQ_SYSTEM_PROMPT = """You are a senior Quantity Surveyor at Buruuj Construction Co. \
Your job is to analyse the attached tender drawing(s) and specifications, \
and produce a structured Bill of Quantities (BOQ) draft.

You must output ONLY valid JSON in the following exact schema, with no \
preamble, no markdown fences, no commentary:

{
  "sections": [
    {
      "code": "1.0",
      "name": "Section name (e.g., Preliminaries)",
      "lines": [
        {
          "item_no": "1.1",
          "description": "Clear description of the work item",
          "uom": "m3" | "m2" | "kg" | "ton" | "no" | "lump_sum" | "lm" | "hour" | "day",
          "quantity": 0.0,
          "trade": "civil" | "mep" | "hvac" | "elec" | "plumb" | "fin" | "paint" | "tile" | "alum" | "road" | "land",
          "notes": "Any clarification or assumption made"
        }
      ]
    }
  ],
  "assumptions": [
    "List any assumptions you made because the drawings/specs were unclear"
  ],
  "missing_info": [
    "List anything you would need to ask in an RFI before pricing"
  ]
}

Guidelines:
- Be exhaustive but realistic. Prefer fewer, well-defined items over many \
  speculative ones.
- Quantity 0.0 is acceptable when you can identify the item but cannot \
  estimate the quantity from the drawing.
- Use logical hierarchical numbering (1.0, 1.1, 1.2, 2.0, 2.1, ...).
- Prefer standard construction trade categories.
- If specifications mention specific products or grades (e.g., "Concrete C30"), \
  include them in the description.
- If the drawing is illegible or insufficient, return a small JSON with mostly \
  empty sections and detailed missing_info entries.
"""


# Map AI's trade codes to actual master trade XML IDs in buruuj_base
TRADE_MAP = {
    'civil': 'buruuj_base.trade_civil',
    'mep': 'buruuj_base.trade_mep',
    'hvac': 'buruuj_base.trade_hvac',
    'elec': 'buruuj_base.trade_elec',
    'plumb': 'buruuj_base.trade_plumb',
    'fin': 'buruuj_base.trade_finish',
    'paint': 'buruuj_base.trade_paint',
    'tile': 'buruuj_base.trade_tile',
    'alum': 'buruuj_base.trade_alum',
    'road': 'buruuj_base.trade_road',
    'land': 'buruuj_base.trade_landscape',
}

# Map UoM strings to Odoo unit XML IDs
UOM_MAP = {
    'm3': 'uom.product_uom_cubic_meter',
    'm2': 'uom.product_uom_square_meter',
    'kg': 'uom.product_uom_kgm',
    'ton': 'uom.product_uom_ton',
    'no': 'uom.product_uom_unit',
    'lump_sum': 'uom.product_uom_unit',
    'lm': 'uom.product_uom_meter',
    'hour': 'uom.product_uom_hour',
    'day': 'uom.product_uom_day',
}


class BuruujBOQ(models.Model):
    _inherit = 'buruuj.boq'

    ai_source_pdf = fields.Binary(
        string='Source Drawings/Spec (PDF)',
        attachment=True,
        help='Upload the tender drawings or specifications. Click \'Draft from '
             'Drawings\' to have AI generate a starter BOQ.')
    ai_source_pdf_name = fields.Char(string='File Name')
    ai_assumptions = fields.Html(
        string='AI Assumptions',
        help='Assumptions the AI made when drafting. Always review before submission.',
        readonly=True)
    ai_missing_info = fields.Html(
        string='Missing Info / Suggested RFIs',
        help='Information the AI flagged as missing. Consider raising RFIs.',
        readonly=True)
    ai_last_task_id = fields.Many2one(
        'buruuj.ai.task', string='Last AI Task', readonly=True)

    def action_ai_draft_boq(self):
        """Send the source PDF to Claude and parse the response into BOQ lines."""
        self.ensure_one()
        if not self.env['buruuj.ai.client'].is_enabled():
            raise UserError(_(
                "AI is not configured. Ask your administrator to set the "
                "Anthropic API key in Settings."))
        if not self.ai_source_pdf:
            raise UserError(_(
                "Please upload the tender drawings/specifications PDF first."))
        if self.state != 'draft':
            raise UserError(_(
                "AI drafting is only available on a Draft BOQ. "
                "Create a new BOQ revision if you want to redraft."))

        # Decode PDF
        import base64
        pdf_bytes = base64.b64decode(self.ai_source_pdf)
        if len(pdf_bytes) > 32 * 1024 * 1024:
            raise UserError(_(
                "PDF is larger than 32 MB. Please split or compress before "
                "uploading."))

        # Build messages
        client = self.env['buruuj.ai.client']
        user_intro = (
            f"Project context: {self.tender_id.title or self.project_id.name or 'Tender'}. "
            f"Currency: {self.currency_id.name}. "
            "Please analyse the attached tender documents and produce a draft BOQ."
        )
        messages = [{
            "role": "user",
            "content": [
                client.make_pdf_block(pdf_bytes),
                client.make_text_block(user_intro),
            ],
        }]

        result = client.complete(
            system=BOQ_SYSTEM_PROMPT,
            messages=messages,
            max_tokens=8192,
            task_type='boq_draft',
            task_record=('buruuj.boq', self.id),
        )

        # Parse JSON, tolerating optional markdown fences
        text = result['text'].strip()
        text = re.sub(r'^```(?:json)?\s*', '', text)
        text = re.sub(r'\s*```\s*$', '', text)

        try:
            parsed = json.loads(text)
        except json.JSONDecodeError as e:
            _logger.error("AI returned non-JSON: %s", text[:500])
            raise UserError(_(
                "AI response was not valid JSON. The task is logged in "
                "AI Tasks for review. Error: %s") % str(e))

        # Apply
        self._apply_ai_boq(parsed)
        self.ai_last_task_id = result['task_id']

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('BOQ Drafted'),
                'message': _('Created %d sections and %d lines. '
                             'Review assumptions and missing info before submission.')
                            % (len(parsed.get('sections', [])),
                               sum(len(s.get('lines', []))
                                   for s in parsed.get('sections', []))),
                'type': 'success',
                'sticky': False,
            },
        }

    def _apply_ai_boq(self, parsed):
        """Take parsed JSON from Claude and create BOQ sections + lines."""
        self.ensure_one()
        Section = self.env['buruuj.boq.section']
        Line = self.env['buruuj.boq.line']
        Rate = self.env['buruuj.rate']

        # Cache trades and uoms
        def _get_xml_id(xml_id):
            try:
                return self.env.ref(xml_id, raise_if_not_found=False)
            except ValueError:
                return False

        section_seq = 10
        line_seq = 10
        for sec_data in parsed.get('sections', []):
            section = Section.create({
                'boq_id': self.id,
                'code': sec_data.get('code', ''),
                'name': sec_data.get('name', 'Untitled Section'),
                'sequence': section_seq,
            })
            section_seq += 10

            for line_data in sec_data.get('lines', []):
                trade_rec = _get_xml_id(TRADE_MAP.get(line_data.get('trade', '')))
                uom_rec = _get_xml_id(UOM_MAP.get(line_data.get('uom', 'no')))

                # Try to match a master rate by description (rough)
                description = line_data.get('description', '')
                rate_rec = False
                if description:
                    matches = Rate.search([
                        ('name', 'ilike', description[:30]),
                    ], limit=1)
                    if matches:
                        rate_rec = matches[0]

                vals = {
                    'boq_id': self.id,
                    'section_id': section.id,
                    'item_no': line_data.get('item_no', ''),
                    'description': description,
                    'quantity': float(line_data.get('quantity') or 0.0),
                    'sequence': line_seq,
                    'notes': line_data.get('notes', ''),
                }
                if uom_rec:
                    vals['uom_id'] = uom_rec.id
                if trade_rec:
                    vals['trade_id'] = trade_rec.id
                if rate_rec:
                    vals['rate_id'] = rate_rec.id
                    vals['unit_rate'] = rate_rec.unit_rate

                Line.create(vals)
                line_seq += 10

        # Capture assumptions and missing info
        assumptions = parsed.get('assumptions', [])
        missing = parsed.get('missing_info', [])
        if assumptions:
            self.ai_assumptions = '<ul>' + ''.join(
                f'<li>{a}</li>' for a in assumptions) + '</ul>'
        if missing:
            self.ai_missing_info = '<ul>' + ''.join(
                f'<li>{m}</li>' for m in missing) + '</ul>'

        # Post a chatter message summarising
        n_sections = len(parsed.get('sections', []))
        n_lines = sum(len(s.get('lines', [])) for s in parsed.get('sections', []))
        self.message_post(body=_(
            "AI drafted %(sections)d sections and %(lines)d lines from the "
            "attached drawings. Review carefully — quantities are estimates "
            "and rates need verification."
        ) % {'sections': n_sections, 'lines': n_lines})
