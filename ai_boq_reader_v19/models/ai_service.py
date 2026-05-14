# -*- coding: utf-8 -*-
"""AI service abstraction for BOQ extraction.

Uses native PDF support on Anthropic Claude (no rasterisation needed) and
on OpenAI for images. Falls back to rasterising PDFs to PNG if the chosen
provider doesn't accept native PDF, or if pdf2image is available and the
user has explicitly opted in via ai_boq.force_rasterize.

Configure via ir.config_parameter:
    ai_boq.provider          -> 'anthropic' | 'openai' | 'azure_openai'
    ai_boq.api_key           -> the provider API key
    ai_boq.model             -> model id (e.g. claude-sonnet-4-5, gpt-4o)
    ai_boq.azure_endpoint    -> only for azure_openai
    ai_boq.force_rasterize   -> 'True' to always convert PDFs to PNG (legacy path)
"""
import base64
import io
import json
import logging
from typing import List, Dict, Any, Tuple

from odoo import models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


SYSTEM_PROMPT = """You are a senior quantity surveyor reading architectural and engineering drawings.

Your job: extract a Bill of Quantities (BOQ) from the provided drawing(s).

Return STRICT JSON ONLY (no prose, no markdown fences) matching this exact schema:
{
  "project_summary": "brief description of what the drawings depict",
  "scale_detected": "drawing scale if visible, e.g. '1:100' or 'unknown'",
  "items": [
    {
      "category": "civil | electrical | plumbing | finishes | structural | other",
      "description": "clear item description (e.g. 'Concrete grade C30 for ground floor slab')",
      "uom": "unit of measure (m, m2, m3, kg, nos, lot, ...)",
      "quantity": <float>,
      "unit_price_estimate": <float, 0 if unknown>,
      "confidence": <float between 0 and 1>,
      "source_reference": "drawing/zone reference, e.g. 'Sheet A-101, Grid B-C'"
    }
  ],
  "warnings": ["any caveats, missing scales, illegible regions, assumptions made"]
}

Rules:
- Be conservative. If you cannot read a dimension, set confidence low and note it in warnings.
- Always include UOM. Use SI units unless the drawing clearly uses imperial.
- Group similar items rather than listing every brick.
- If multiple drawings are supplied, treat them as one project and de-duplicate items.
- Never invent prices. If you have no basis, set unit_price_estimate to 0.
- Include all material take-offs even when only implied by drawn elements
  (slab volume, wall area, ceiling area, paint area, etc.).
"""

# Anthropic native PDF limits
MAX_PDF_BYTES = 32 * 1024 * 1024
MAX_PDF_PAGES_HARD = 100


class AIService(models.AbstractModel):
    _name = 'ai.boq.service'
    _description = 'AI Service for BOQ Extraction'

    # --------------------------------------------------------------------- #
    # Public API
    # --------------------------------------------------------------------- #
    def analyze_design(self, file_b64, filename: str) -> Dict[str, Any]:
        """Analyse a design file and return parsed BOQ data.

        :param file_b64: base64-encoded file bytes (PDF or image), as stored
            in an Odoo Binary field. Already base64; do NOT re-encode.
        :param filename: original filename, used to detect type
        :return: dict matching the JSON schema in SYSTEM_PROMPT
        :raises UserError: on configuration or provider errors
        """
        if not file_b64:
            raise UserError(_("No file data provided to analyse."))

        provider, api_key, model = self._get_config()
        force_raster = self.env['ir.config_parameter'].sudo()\
            .get_param('ai_boq.force_rasterize', default='False') == 'True'

        # Validate the file BEFORE any API call. Catches double-encoding,
        # renamed files, encrypted PDFs, oversize, etc., with clear errors.
        kind, raw_bytes, clean_b64 = self._validate_and_classify(file_b64, filename)

        _logger.info("BOQ AI: provider=%s model=%s kind=%s size=%dKB",
                     provider, model, kind, len(raw_bytes) // 1024)

        # Choose transport.
        # - Anthropic + PDF → native document block (no poppler needed)
        # - OpenAI + PDF    → rasterise (Chat Completions doesn't accept PDF)
        # - either + image  → image block
        # - force_raster    → rasterise unconditionally
        if kind == 'pdf' and provider == 'anthropic' and not force_raster:
            payload = [self._anthropic_pdf_block(clean_b64)]
        elif kind == 'pdf':
            images = self._rasterise_pdf(raw_bytes)
            payload = [self._image_block(provider, b) for b in images]
        else:  # image
            payload = [self._image_block(provider, clean_b64)]

        # one retry on JSON parse failure
        last_err = None
        for attempt in range(2):
            try:
                raw = self._call_provider(provider, api_key, model, payload, attempt > 0)
                data = self._parse_json(raw)
                data['_meta'] = {
                    'provider': provider,
                    'model': model,
                    'pages': len(payload),
                    'raw_response': raw[:8000],
                }
                return data
            except json.JSONDecodeError as e:
                last_err = e
                _logger.warning("BOQ AI: JSON parse failed (attempt %s): %s", attempt + 1, e)
        raise UserError(_("AI returned malformed JSON after retry: %s") % last_err)

    # --------------------------------------------------------------------- #
    # File validation — runs BEFORE any API call
    # --------------------------------------------------------------------- #
    def _validate_and_classify(self, file_b64, filename) -> Tuple[str, bytes, str]:
        """Returns (kind, raw_bytes, clean_base64).

        kind is 'pdf' or 'image'. Raises UserError with a precise message
        for any of the common breakage modes.
        """
        # Normalise: file_b64 may arrive as bytes or str depending on caller
        if isinstance(file_b64, bytes):
            b64_str = file_b64.decode('ascii', errors='replace')
        else:
            b64_str = file_b64

        # Strip data-URI prefix if present
        if b64_str.startswith('data:'):
            b64_str = b64_str.split(',', 1)[-1]

        try:
            raw = base64.b64decode(b64_str, validate=False)
        except Exception as e:
            raise UserError(_(
                "Could not base64-decode the uploaded file (%s).\n"
                "If you wrapped the bytes in base64 manually before saving, remove that step — "
                "Odoo's Binary field already stores base64."
            ) % e)

        if len(raw) < 8:
            raise UserError(_("Uploaded file is empty or truncated (%d bytes).") % len(raw))

        head = raw[:8]
        ext = (filename or '').lower().rsplit('.', 1)[-1]

        # PDF
        if head[:5] == b'%PDF-':
            if len(raw) > MAX_PDF_BYTES:
                raise UserError(_(
                    "PDF is too large (%.1f MB). Anthropic's API caps PDFs at %d MB. "
                    "Re-export at a lower DPI or split into multiple files."
                ) % (len(raw) / 1024 / 1024, MAX_PDF_BYTES // 1024 // 1024))
            if b'/Encrypt' in raw[:4096] or b'/Encrypt' in raw[-4096:]:
                raise UserError(_(
                    "PDF appears to be encrypted/password-protected. "
                    "Re-save it without encryption (in your PDF viewer: File → Export → uncheck password)."
                ))
            return 'pdf', raw, b64_str

        # Images
        if head[:8] == b'\x89PNG\r\n\x1a\n':
            return 'image', raw, b64_str
        if head[:3] == b'\xff\xd8\xff':       # JPEG
            return 'image', raw, b64_str
        if head[:4] == b'RIFF' and len(raw) >= 12 and raw[8:12] == b'WEBP':
            return 'image', raw, b64_str
        if head[:6] in (b'GIF87a', b'GIF89a'):
            return 'image', raw, b64_str

        # Most common screw-up: file-extension lies
        if ext == 'pdf':
            preview = raw[:32].decode('latin-1', errors='replace')
            raise UserError(_(
                "File '%s' has a .pdf extension but is not a valid PDF.\n"
                "First bytes: %r\n"
                "Likely causes: the file is actually HTML/Word renamed to .pdf, "
                "or the upload was double-base64-encoded somewhere in your code path."
            ) % (filename, preview))

        raise UserError(_(
            "Unsupported or unrecognised file type for '%s'. "
            "Supported: PDF, PNG, JPEG, WebP, GIF."
        ) % filename)

    # --------------------------------------------------------------------- #
    # Configuration
    # --------------------------------------------------------------------- #
    def _get_config(self):
        ICP = self.env['ir.config_parameter'].sudo()
        provider = ICP.get_param('ai_boq.provider', default='anthropic')
        api_key = ICP.get_param('ai_boq.api_key', default='')
        default_model = {
            'anthropic': 'claude-sonnet-4-5',
            'openai': 'gpt-4o',
            'azure_openai': 'gpt-4o',
        }.get(provider, 'claude-sonnet-4-5')
        model = ICP.get_param('ai_boq.model', default=default_model)
        if not api_key:
            raise UserError(_(
                "No API key configured for the AI BOQ Reader.\n"
                "Go to Settings → BOQ AI Reader and set the API key."
            ))
        return provider, api_key, model

    # --------------------------------------------------------------------- #
    # Content block builders
    # --------------------------------------------------------------------- #
    def _anthropic_pdf_block(self, clean_b64: str) -> dict:
        return {
            "type": "document",
            "source": {
                "type": "base64",
                "media_type": "application/pdf",
                "data": clean_b64,
            },
        }

    def _image_block(self, provider: str, b64_data) -> dict:
        if isinstance(b64_data, bytes):
            b64_data = b64_data.decode('ascii')
        if provider == 'anthropic':
            return {
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": "image/png",
                    "data": b64_data,
                },
            }
        return {
            "type": "image_url",
            "image_url": {"url": f"data:image/png;base64,{b64_data}"},
        }

    # --------------------------------------------------------------------- #
    # PDF rasterisation (only used for OpenAI or force_rasterize)
    # --------------------------------------------------------------------- #
    def _rasterise_pdf(self, raw: bytes) -> List[str]:
        """Convert PDF bytes to a list of base64-PNG strings, one per page."""
        try:
            from pdf2image import convert_from_bytes
        except ImportError:
            raise UserError(_(
                "Cannot send PDFs to this provider without rasterisation, "
                "and pdf2image is not installed.\n"
                "Either:\n"
                "  • Switch provider to Anthropic (supports PDFs natively), or\n"
                "  • Install: pip install pdf2image  +  apt install poppler-utils"
            ))
        try:
            pages = convert_from_bytes(raw, dpi=200, fmt='png')
        except Exception as e:
            raise UserError(_("Failed to rasterise PDF: %s") % e)
        pages = pages[:25]  # cost cap
        out = []
        for p in pages:
            buf = io.BytesIO()
            p.save(buf, format='PNG')
            out.append(base64.b64encode(buf.getvalue()).decode('ascii'))
        return out

    # --------------------------------------------------------------------- #
    # Provider dispatch
    # --------------------------------------------------------------------- #
    def _call_provider(self, provider, api_key, model, content_blocks, strict_retry):
        if provider == 'anthropic':
            return self._call_anthropic(api_key, model, content_blocks, strict_retry)
        if provider in ('openai', 'azure_openai'):
            return self._call_openai(api_key, model, content_blocks, provider, strict_retry)
        raise UserError(_("Unknown AI provider: %s") % provider)

    def _call_anthropic(self, api_key, model, content_blocks, strict_retry):
        try:
            import anthropic
        except ImportError:
            raise UserError(_("anthropic package not installed. Run: pip install anthropic"))

        client = anthropic.Anthropic(api_key=api_key)
        user_text = "Analyse the attached drawings and return the BOQ JSON now."
        if strict_retry:
            user_text += " Your previous response was not valid JSON. Return ONLY the JSON object, no other text."
        full_content = list(content_blocks) + [{"type": "text", "text": user_text}]

        try:
            resp = client.messages.create(
                model=model,
                max_tokens=4096,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": full_content}],
            )
        except anthropic.BadRequestError as e:
            # Surface the exact field path Anthropic complains about
            raise UserError(_("Anthropic rejected the request: %s") % e)
        return "".join(b.text for b in resp.content if getattr(b, 'type', None) == 'text')

    def _call_openai(self, api_key, model, content_blocks, provider, strict_retry):
        try:
            from openai import OpenAI, AzureOpenAI
        except ImportError:
            raise UserError(_("openai package not installed. Run: pip install openai"))

        if provider == 'azure_openai':
            endpoint = self.env['ir.config_parameter'].sudo().get_param('ai_boq.azure_endpoint')
            if not endpoint:
                raise UserError(_("ai_boq.azure_endpoint must be set for azure_openai provider."))
            client = AzureOpenAI(api_key=api_key, azure_endpoint=endpoint,
                                 api_version="2024-08-01-preview")
        else:
            client = OpenAI(api_key=api_key)

        text = ("Analyse the attached drawings and return the BOQ JSON now."
                + (" JSON ONLY." if strict_retry else ""))
        full_content = [{"type": "text", "text": text}] + list(content_blocks)

        resp = client.chat.completions.create(
            model=model,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": full_content},
            ],
            max_tokens=4096,
        )
        return resp.choices[0].message.content or ""

    # --------------------------------------------------------------------- #
    # JSON parsing (tolerant)
    # --------------------------------------------------------------------- #
    def _parse_json(self, raw: str) -> Dict[str, Any]:
        text = (raw or '').strip()
        if text.startswith('```'):
            text = text.strip('`')
            if text.lower().startswith('json'):
                text = text[4:]
            text = text.strip()
            if text.endswith('```'):
                text = text[:-3].strip()
        if not text.startswith('{'):
            start = text.find('{')
            end = text.rfind('}')
            if start != -1 and end != -1 and end > start:
                text = text[start:end + 1]
        return json.loads(text)
