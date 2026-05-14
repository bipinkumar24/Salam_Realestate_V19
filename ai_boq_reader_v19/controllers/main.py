# -*- coding: utf-8 -*-
"""Optional REST endpoint for triggering BOQ analysis from external systems."""
import base64
import json
import logging

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


class BoqController(http.Controller):

    @http.route('/ai_boq/analyze', type='jsonrpc', auth='user', methods=['POST'], csrf=False)
    def analyze(self, filename=None, file_b64=None, partner_id=None, project_id=None):
        """Create a BOQ project from a base64 file payload and trigger analysis.

        Returns: {"id": <project_id>, "name": <ref>, "lines": <count>, "total": <amount>}
        """
        if not (filename and file_b64):
            return {'error': 'filename and file_b64 are required'}
        env = request.env
        rec = env['ai.boq.project'].create({
            'name': 'New',
            'partner_id': partner_id or False,
            'project_id': project_id or False,
            'design_filename': filename,
            'design_file': file_b64,
        })
        try:
            rec.action_analyze()
        except Exception as e:
            _logger.exception("BOQ analysis failed")
            return {'id': rec.id, 'error': str(e)}
        return {
            'id': rec.id,
            'name': rec.name,
            'lines': rec.line_count,
            'total': rec.total_amount,
            'currency': rec.currency_id.name,
        }
