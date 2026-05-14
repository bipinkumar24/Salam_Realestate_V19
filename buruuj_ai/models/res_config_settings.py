# -*- coding: utf-8 -*-
from odoo import models, fields


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    buruuj_ai_anthropic_api_key = fields.Char(
        string='Anthropic API Key',
        config_parameter='buruuj_ai.anthropic_api_key',
        help='Your Anthropic API key. Get one from https://console.anthropic.com.')
    buruuj_ai_model = fields.Selection([
        ('claude-opus-4-7', 'Claude Opus 4.7 (most capable)'),
        ('claude-opus-4-6', 'Claude Opus 4.6'),
        ('claude-sonnet-4-6', 'Claude Sonnet 4.6 (faster, cheaper)'),
        ('claude-haiku-4-5-20251001', 'Claude Haiku 4.5 (fastest, cheapest)'),
    ], string='Default AI Model',
       config_parameter='buruuj_ai.model',
       default='claude-opus-4-7')
    buruuj_ai_monthly_budget_usd = fields.Float(
        string='Monthly Budget (USD)',
        config_parameter='buruuj_ai.monthly_budget_usd',
        default=500.0,
        help='Soft cap. The system will warn when monthly spend approaches this.')
    buruuj_ai_enable_boq_draft = fields.Boolean(
        string='Enable BOQ Drafting from Drawings',
        config_parameter='buruuj_ai.enable_boq_draft',
        default=True)
    buruuj_ai_enable_ncr_draft = fields.Boolean(
        string='Enable NCR Drafting from Photos',
        config_parameter='buruuj_ai.enable_ncr_draft',
        default=True)
    buruuj_ai_enable_sub_recommend = fields.Boolean(
        string='Enable Subcontractor Recommendations',
        config_parameter='buruuj_ai.enable_sub_recommend',
        default=True)
    buruuj_ai_enable_vo_draft = fields.Boolean(
        string='Enable VO Drafting',
        config_parameter='buruuj_ai.enable_vo_draft',
        default=True)

    # ----- Cron toggles -----
    buruuj_ai_cron_license_scan_enabled = fields.Boolean(
        string='Daily License Expiry Scan',
        config_parameter='buruuj_ai.cron_license_scan_enabled',
        default=True)
    buruuj_ai_cron_contract_scan_enabled = fields.Boolean(
        string='Daily Contract Key Dates Scan',
        config_parameter='buruuj_ai.cron_contract_scan_enabled',
        default=True)
    buruuj_ai_cron_rfi_scan_enabled = fields.Boolean(
        string='Daily Overdue RFI Scan',
        config_parameter='buruuj_ai.cron_rfi_scan_enabled',
        default=True)
    buruuj_ai_cron_portfolio_scan_enabled = fields.Boolean(
        string='Weekly Portfolio Risk Scan (AI)',
        config_parameter='buruuj_ai.cron_portfolio_scan_enabled',
        default=True)
    buruuj_ai_cron_scorecard_reminder_enabled = fields.Boolean(
        string='Weekly Scorecard Reminder',
        config_parameter='buruuj_ai.cron_scorecard_reminder_enabled',
        default=True)
    buruuj_ai_license_warning_days = fields.Integer(
        string='License Warning Window (days)',
        config_parameter='buruuj_ai.license_warning_days',
        default=30)
    buruuj_ai_contract_warning_days = fields.Integer(
        string='Contract Warning Window (days)',
        config_parameter='buruuj_ai.contract_warning_days',
        default=30)
