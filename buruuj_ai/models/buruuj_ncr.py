# -*- coding: utf-8 -*-
"""Add AI drafting button to NCRs.

A site engineer takes a photo of a defect with their phone, attaches it,
clicks 'Draft from Photo'. Claude analyses the image and drafts the
description, root cause, and corrective action."""
import json
import logging
import re
from odoo import models, fields, api, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


NCR_SYSTEM_PROMPT = """You are a senior Quality Engineer at Buruuj Construction Co. \
Your job is to look at the attached photo(s) of a construction defect and draft \
a Non-Conformance Report (NCR).

You must output ONLY valid JSON in the following exact schema, with no \
preamble, no markdown fences, no commentary:

{
  "title": "Short factual title, max 80 characters",
  "severity": "minor" | "major" | "critical",
  "description": "Plain-text description of what is visible in the photo, \
including approximate dimensions if estimable, location clues, and what \
specification or drawing requirement appears to be violated",
  "root_cause": "Most likely root cause based on what is visible. Be specific \
about workmanship, material, design, or supervision factors",
  "corrective_action": "Specific steps to fix THIS instance. Practical, \
sequenced, and verifiable",
  "preventive_action": "What should change going forward to prevent recurrence \
on this project and others"
}

Severity guide:
- minor: Cosmetic, no structural or functional impact
- major: Affects function, durability, or significant rework needed
- critical: Structural integrity, safety, or major contractual implications

Be conservative with severity. Only use 'critical' when there is clear \
evidence of structural or safety risk visible in the photo.

If the photo is too unclear to assess, return:
{
  "title": "Photo unclear — manual assessment required",
  "severity": "minor",
  "description": "The photo provided is not clear enough to assess the defect.",
  "root_cause": "",
  "corrective_action": "Re-photograph with better lighting and closer view.",
  "preventive_action": ""
}
"""


class BuruujNCR(models.Model):
    _inherit = 'buruuj.ncr'

    ai_source_photo = fields.Binary(
        string='Defect Photo',
        attachment=True,
        help='Photo of the defect. Click \'Draft from Photo\' to have AI '
             'pre-fill the NCR fields.')
    ai_source_photo_name = fields.Char(string='Photo File Name')
    ai_last_task_id = fields.Many2one(
        'buruuj.ai.task', string='Last AI Task', readonly=True)

    def action_ai_draft_ncr(self):
        """Send the photo to Claude and pre-fill description/root cause/action."""
        self.ensure_one()
        if not self.env['buruuj.ai.client'].is_enabled():
            raise UserError(_(
                "AI is not configured. Ask your administrator to set the "
                "Anthropic API key in Settings."))
        if not self.ai_source_photo:
            raise UserError(_(
                "Please attach a photo of the defect first."))
        if self.state not in ('draft',):
            raise UserError(_(
                "AI drafting is only available on a Draft NCR."))

        import base64
        image_bytes = base64.b64decode(self.ai_source_photo)
        if len(image_bytes) > 5 * 1024 * 1024:
            raise UserError(_(
                "Photo is larger than 5 MB. Please reduce the resolution before "
                "uploading."))

        # Detect media type from filename
        fname = (self.ai_source_photo_name or '').lower()
        if fname.endswith('.png'):
            media_type = 'image/png'
        elif fname.endswith('.gif'):
            media_type = 'image/gif'
        elif fname.endswith('.webp'):
            media_type = 'image/webp'
        else:
            media_type = 'image/jpeg'

        client = self.env['buruuj.ai.client']
        context = (
            f"Project: {self.project_id.name or 'Unspecified'}. "
            f"Reported by: {self.raised_by.name or 'Unknown'}. "
            f"Location on site (if known): {self.location or 'Not specified'}. "
            "Please assess the attached photo and draft the NCR."
        )
        messages = [{
            "role": "user",
            "content": [
                client.make_image_block(image_bytes, media_type=media_type),
                client.make_text_block(context),
            ],
        }]

        result = client.complete(
            system=NCR_SYSTEM_PROMPT,
            messages=messages,
            max_tokens=2048,
            task_type='ncr_draft',
            task_record=('buruuj.ncr', self.id),
        )

        text = result['text'].strip()
        text = re.sub(r'^```(?:json)?\s*', '', text)
        text = re.sub(r'\s*```\s*$', '', text)

        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            _logger.error("AI returned non-JSON: %s", text[:500])
            raise UserError(_(
                "AI response was not valid JSON. Try retaking the photo or "
                "fill in the NCR manually."))

        # Apply, but never overwrite a field the user has already filled
        updates = {}
        if not self.title and parsed.get('title'):
            updates['title'] = parsed['title'][:200]
        if parsed.get('severity') in ('minor', 'major', 'critical'):
            # Severity can be overwritten — AI should be the suggestion
            updates['severity'] = parsed['severity']
        if not self.description and parsed.get('description'):
            updates['description'] = f"<p>{parsed['description']}</p>"
        if not self.root_cause and parsed.get('root_cause'):
            updates['root_cause'] = f"<p>{parsed['root_cause']}</p>"
        if not self.corrective_action and parsed.get('corrective_action'):
            updates['corrective_action'] = f"<p>{parsed['corrective_action']}</p>"
        if not self.preventive_action and parsed.get('preventive_action'):
            updates['preventive_action'] = f"<p>{parsed['preventive_action']}</p>"

        updates['ai_last_task_id'] = result['task_id']
        self.write(updates)

        self.message_post(body=_(
            "AI drafted this NCR from the attached photo. "
            "Verify all fields before issuing — AI assessment is a starting "
            "point, not a final judgement."))

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('NCR Drafted'),
                'message': _('Severity suggested: %s. Review all fields before issuing.')
                            % parsed.get('severity', 'unknown'),
                'type': 'success',
                'sticky': False,
            },
        }
