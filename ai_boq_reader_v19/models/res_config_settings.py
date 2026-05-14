# -*- coding: utf-8 -*-
from odoo import models, fields, api


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    ai_boq_provider = fields.Selection([
        ('anthropic', 'Anthropic Claude'),
        ('openai', 'OpenAI'),
        ('azure_openai', 'Azure OpenAI'),
    ], string='AI Provider', default='anthropic',
       config_parameter='ai_boq.provider')
    ai_boq_api_key = fields.Char(string='AI API Key', config_parameter='ai_boq.api_key')
    ai_boq_model = fields.Char(string='Model ID', config_parameter='ai_boq.model',
                               help="e.g. claude-sonnet-4-5 or gpt-4o")
    ai_boq_azure_endpoint = fields.Char(string='Azure Endpoint',
                                        config_parameter='ai_boq.azure_endpoint',
                                        help="Required when provider is Azure OpenAI.")
    ai_boq_auto_create_so = fields.Boolean(
        string='Auto-create Sales Order on approval',
        config_parameter='ai_boq.auto_create_so')
    ai_boq_use_queue_job = fields.Boolean(
        string='Run AI analysis asynchronously (queue_job)',
        config_parameter='ai_boq.use_queue_job',
        help="Requires the OCA queue_job module to be installed and a worker running. "
             "When enabled, hitting Analyse dispatches the AI call to a background job.")
