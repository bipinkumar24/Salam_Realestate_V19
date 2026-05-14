# -*- coding: utf-8 -*-
"""Central AI client for Buruuj.

Wraps the Anthropic Claude API with:
- Configurable model and API key (from ir.config_parameter)
- Standardised error handling
- Token usage logging via buruuj.ai.task
- Support for vision (PDFs and images) inputs
"""
import base64
import logging
from odoo import models, fields, api, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

try:
    import anthropic
    HAS_ANTHROPIC = True
except ImportError:
    HAS_ANTHROPIC = False
    _logger.warning(
        "The 'anthropic' Python package is not installed. "
        "Buruuj AI features will be disabled. "
        "Install with: pip install anthropic")


# Default model — can be overridden via config parameter buruuj_ai.model
DEFAULT_MODEL = 'claude-opus-4-7'
# Conservative max tokens for output
DEFAULT_MAX_TOKENS = 4096


class BuruujAIClient(models.AbstractModel):
    """Singleton service for invoking Claude.

    Use via: self.env['buruuj.ai.client'].complete(...) — never instantiate."""
    _name = 'buruuj.ai.client'
    _description = 'Buruuj AI Client (Anthropic Claude)'

    # ------------------------------------------------------------------
    # Configuration helpers
    # ------------------------------------------------------------------
    @api.model
    def _get_api_key(self):
        """Return the API key from config or raise."""
        ICP = self.env['ir.config_parameter'].sudo()
        key = ICP.get_param('buruuj_ai.anthropic_api_key', '').strip()
        if not key:
            raise UserError(_(
                "Anthropic API key is not configured. "
                "Go to Construction → Configuration → Settings → AI Assistant "
                "and enter your API key."))
        return key

    @api.model
    def _get_model(self):
        ICP = self.env['ir.config_parameter'].sudo()
        return ICP.get_param('buruuj_ai.model', DEFAULT_MODEL)

    @api.model
    def _get_client(self):
        """Return an Anthropic SDK client. Raises if not installed."""
        if not HAS_ANTHROPIC:
            raise UserError(_(
                "The 'anthropic' Python package is required for AI features. "
                "Ask your administrator to run: pip install anthropic"))
        return anthropic.Anthropic(api_key=self._get_api_key())

    @api.model
    def is_enabled(self):
        """True if AI is enabled and configured. Used to hide UI buttons."""
        if not HAS_ANTHROPIC:
            return False
        ICP = self.env['ir.config_parameter'].sudo()
        return bool(ICP.get_param('buruuj_ai.anthropic_api_key', '').strip())

    # ------------------------------------------------------------------
    # Core completion call
    # ------------------------------------------------------------------
    @api.model
    def complete(self, system, messages, max_tokens=DEFAULT_MAX_TOKENS,
                 task_type='generic', task_record=None):
        """Send a completion request to Claude.

        :param system: System prompt (string).
        :param messages: List of message dicts in Anthropic format.
            Each: {"role": "user"|"assistant", "content": str | [blocks]}
        :param max_tokens: Max output tokens (default 4096).
        :param task_type: One of 'boq_draft', 'ncr_draft', 'sub_recommend',
            'vo_draft', 'generic'. Used for logging.
        :param task_record: Optional record (model, id) tuple to link the task.
        :return: dict with keys:
            - text: assembled text from all text content blocks
            - input_tokens, output_tokens: usage counters
            - task_id: the buruuj.ai.task record id
            - raw: the full response object (for advanced use)
        """
        client = self._get_client()
        model = self._get_model()

        # Create task record up-front so we have something to log against
        task_vals = {
            'task_type': task_type,
            'state': 'running',
            'model': model,
            'system_prompt': (system or '')[:8000],
        }
        if task_record:
            task_vals['ref_model'] = task_record[0]
            task_vals['ref_id'] = task_record[1]
        task = self.env['buruuj.ai.task'].create(task_vals)

        try:
            response = client.messages.create(
                model=model,
                max_tokens=max_tokens,
                system=system,
                messages=messages,
            )
        except anthropic.APIError as e:
            task.write({
                'state': 'failed',
                'error_message': str(e)[:2000],
            })
            _logger.exception("Anthropic API error")
            raise UserError(_("AI request failed: %s") % str(e))
        except Exception as e:
            task.write({
                'state': 'failed',
                'error_message': str(e)[:2000],
            })
            _logger.exception("Unexpected AI error")
            raise UserError(_("Unexpected error calling AI: %s") % str(e))

        # Extract text content
        text_parts = []
        for block in response.content:
            if hasattr(block, 'text'):
                text_parts.append(block.text)
        text = "".join(text_parts)

        # Log usage
        in_tokens = response.usage.input_tokens
        out_tokens = response.usage.output_tokens
        task.write({
            'state': 'done',
            'input_tokens': in_tokens,
            'output_tokens': out_tokens,
            'response_text': text[:32000],
        })

        return {
            'text': text,
            'input_tokens': in_tokens,
            'output_tokens': out_tokens,
            'task_id': task.id,
            'raw': response,
        }

    # ------------------------------------------------------------------
    # Helpers for building vision messages (PDF + image)
    # ------------------------------------------------------------------
    @api.model
    def make_pdf_block(self, pdf_bytes):
        """Return an Anthropic content block for a PDF document."""
        return {
            "type": "document",
            "source": {
                "type": "base64",
                "media_type": "application/pdf",
                "data": base64.b64encode(pdf_bytes).decode('ascii'),
            },
        }

    @api.model
    def make_image_block(self, image_bytes, media_type='image/jpeg'):
        """Return an Anthropic content block for an image.

        :param media_type: One of image/jpeg, image/png, image/gif, image/webp."""
        return {
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": media_type,
                "data": base64.b64encode(image_bytes).decode('ascii'),
            },
        }

    @api.model
    def make_text_block(self, text):
        return {"type": "text", "text": text}
