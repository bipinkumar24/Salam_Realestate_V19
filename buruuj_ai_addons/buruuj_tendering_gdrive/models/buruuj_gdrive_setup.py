# -*- coding: utf-8 -*-
from odoo import api, fields, models


class BuruujGdriveSetup(models.TransientModel):
    _name = 'buruuj.gdrive.setup'
    _description = 'Buruuj Master Rates — Google Drive Sync Configuration'

    folder_id = fields.Char(string='Drive Folder ID', required=True,
                            help='ID portion of the Drive folder URL: drive.google.com/drive/folders/<this part>')
    filename = fields.Char(string='Filename in Drive',
                           default='buruuj_master_rates.xlsx', required=True)
    service_account = fields.Binary(
        string='Service Account JSON',
        help='Upload the service account JSON key file. Share the target Drive folder with the account email.')
    service_account_filename = fields.Char()
    anthropic_api_key = fields.Char(
        string='Anthropic API Key',
        help='Used by "Generate with Claude" on the Master Rates list.')
    has_existing_credentials = fields.Boolean(compute='_compute_existing_creds')

    @api.depends_context('uid')
    def _compute_existing_creds(self):
        existing = self.env['ir.config_parameter'].sudo().get_param(
            'buruuj_tendering_gdrive.service_account_json')
        for rec in self:
            rec.has_existing_credentials = bool(existing)

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        cp = self.env['ir.config_parameter'].sudo()
        if 'folder_id' in fields_list:
            res['folder_id'] = cp.get_param('buruuj_tendering_gdrive.folder_id', '')
        if 'filename' in fields_list:
            res['filename'] = cp.get_param(
                'buruuj_tendering_gdrive.filename', 'buruuj_master_rates.xlsx')
        if 'anthropic_api_key' in fields_list:
            existing = cp.get_param('buruuj_tendering_gdrive.anthropic_api_key', '')
            res['anthropic_api_key'] = ('***configured***' if existing else '')
        return res

    def action_save(self):
        self.ensure_one()
        cp = self.env['ir.config_parameter'].sudo()
        cp.set_param('buruuj_tendering_gdrive.folder_id', self.folder_id)
        cp.set_param('buruuj_tendering_gdrive.filename', self.filename)
        if self.service_account:
            value = self.service_account
            if isinstance(value, bytes):
                value = value.decode('ascii')
            cp.set_param('buruuj_tendering_gdrive.service_account_json', value)
        if self.anthropic_api_key and self.anthropic_api_key != '***configured***':
            cp.set_param(
                'buruuj_tendering_gdrive.anthropic_api_key', self.anthropic_api_key)
        return {'type': 'ir.actions.act_window_close'}
