# -*- coding: utf-8 -*-
from odoo import models, fields


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    # Default retention and advance percentages used as suggestions
    buruuj_retention_percent = fields.Float(
        string='Default Retention %',
        config_parameter='buruuj.buruuj_retention_percent',
        default=10.0)
    buruuj_advance_percent = fields.Float(
        string='Default Advance Payment %',
        config_parameter='buruuj.buruuj_advance_percent',
        default=20.0)
    buruuj_dlp_months = fields.Integer(
        string='Default Defects Liability Period (months)',
        config_parameter='buruuj.buruuj_dlp_months',
        default=12)
    enable_geofence_attendance = fields.Boolean(
        string='Enable Geofenced Site Attendance',
        config_parameter='buruuj.enable_geofence_attendance',
        default=True)
