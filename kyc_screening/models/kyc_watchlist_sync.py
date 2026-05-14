# -*- coding: utf-8 -*-
"""
KYC Watchlist Sync Engine
Sources (priority order):
  1. Google Sheets  — spreadsheet hosted on Google Drive (primary)
  2. Google Drive   — plain CSV file on Google Drive (fallback)
  3. Dropbox        — CSV in standard Dropbox (fallback)
  4. Dropbox Sandbox— CSV in Dropbox sandbox environment (fallback)
  5. Stale cache    — last successful download stored in ir.attachment
  6. 503 error      — no data available

Uses only Python stdlib urllib. No external packages required.
"""
import json
import logging
import urllib.request
import urllib.parse
import urllib.error
import base64
from typing import Optional
from datetime import datetime, timezone
from odoo import models, fields, api, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class KYCWatchlistSync(models.Model):
    """
    Manages the watchlist sync state and refresh logic.
    Single-row singleton — use get_singleton() to access.
    """
    _name        = 'kyc.watchlist.sync'
    _description = 'KYC Watchlist Sync State'

    name        = fields.Char(default='KYC Sync', readonly=True)

    # ── Watchlist (sanctions list) ────────────────────────────────────
    last_sync        = fields.Datetime(string='Watchlist Last Sync', readonly=True)
    last_source      = fields.Selection([
        ('google_sheets',   'Google Sheets'),
        ('google_drive',    'Google Drive (CSV)'),
        ('dropbox',         'Dropbox'),
        ('dropbox_sandbox', 'Dropbox Sandbox'),
        ('stale_cache',     'Stale Cache (offline)'),
    ], string='Watchlist Source', readonly=True)
    entry_count      = fields.Integer(string='Watchlist Entries', readonly=True)
    stale            = fields.Boolean(string='Watchlist Stale',
                                      default=False, readonly=True)
    last_error       = fields.Text(string='Watchlist Last Error', readonly=True)

    # ── Bank Approved List ────────────────────────────────────────────
    approved_last_sync   = fields.Datetime(string='Approved List Last Sync', readonly=True)
    approved_last_source = fields.Selection([
        ('google_sheets',   'Google Sheets'),
        ('google_drive',    'Google Drive (CSV)'),
        ('dropbox',         'Dropbox'),
        ('dropbox_sandbox', 'Dropbox Sandbox'),
        ('stale_cache',     'Stale Cache (offline)'),
    ], string='Approved List Source', readonly=True)
    approved_count       = fields.Integer(string='Approved Entries', readonly=True)
    approved_stale       = fields.Boolean(string='Approved List Stale',
                                          default=False, readonly=True)
    approved_last_error  = fields.Text(string='Approved List Last Error', readonly=True)

    @api.model
    def get_singleton(self):
        rec = self.search([], limit=1)
        if not rec:
            rec = self.create({'name': 'KYC Sync'})
        return rec

    # ── Scheduled + manual actions ───────────────────────────────────────
    @api.model
    def action_scheduled_sync(self):
        """Called by ir.cron every N minutes."""
        self.get_singleton()._do_sync()

    def action_manual_sync(self):
        self.ensure_one()
        self._do_sync()
        return {
            'type': 'ir.actions.client',
            'tag':  'display_notification',
            'params': {
                'title':   _('KYC Sync Complete'),
                'message': _(
                    'Watchlist: %d entries (%s) | Approved List: %d entries (%s)'
                ) % (
                    self.entry_count,    self.last_source        or '?',
                    self.approved_count, self.approved_last_source or '?',
                ),
                'sticky': False,
                'type': 'warning' if (self.stale or self.approved_stale) else 'success',
            }
        }

    # ── Core sync — syncs BOTH lists independently ───────────────────────
    def _do_sync(self):
        config = self.env['ir.config_parameter'].sudo()

        # Mint Google OAuth2 token once — shared by all Google sources
        gdrive_token = None
        sa_path = config.get_param('kyc.gdrive.service_account_path', '')
        if sa_path:
            try:
                with open(sa_path, 'r') as fh:
                    sa = json.load(fh)
                gdrive_token = self._gdrive_get_token(sa)
            except Exception as exc:
                _logger.warning('KYC: Could not load service account: %s', exc)

        # Sync watchlist (sanctions list)
        self._sync_one_list(
            config        = config,
            gdrive_token  = gdrive_token,
            list_label    = 'Watchlist',
            model_name    = 'kyc.watchlist.entry',
            cache_name    = 'kyc_watchlist_cache.csv',
            param_sheets_id   = 'kyc.gsheets.spreadsheet_id',
            param_sheet_name  = 'kyc.gsheets.sheet_name',
            param_drive_id    = 'kyc.gdrive.file_id',
            param_dbx_token   = 'kyc.dropbox.access_token',
            param_dbx_path    = 'kyc.dropbox.file_path',
            param_sbx_token   = 'kyc.dropbox.sandbox_token',
            param_sbx_path    = 'kyc.dropbox.sandbox_file_path',
            param_sbx_ns      = 'kyc.dropbox.sandbox_namespace',
            field_last_sync   = 'last_sync',
            field_last_source = 'last_source',
            field_count       = 'entry_count',
            field_stale       = 'stale',
            field_error       = 'last_error',
        )

        # Sync bank approved list (separate sources)
        self._sync_one_list(
            config        = config,
            gdrive_token  = gdrive_token,
            list_label    = 'Approved List',
            model_name    = 'kyc.approved.entry',
            cache_name    = 'kyc_approved_cache.csv',
            param_sheets_id   = 'kyc.approved.gsheets.spreadsheet_id',
            param_sheet_name  = 'kyc.approved.gsheets.sheet_name',
            param_drive_id    = 'kyc.approved.gdrive.file_id',
            param_dbx_token   = 'kyc.approved.dropbox.access_token',
            param_dbx_path    = 'kyc.approved.dropbox.file_path',
            param_sbx_token   = 'kyc.approved.dropbox.sandbox_token',
            param_sbx_path    = 'kyc.approved.dropbox.sandbox_file_path',
            param_sbx_ns      = 'kyc.approved.dropbox.sandbox_namespace',
            field_last_sync   = 'approved_last_sync',
            field_last_source = 'approved_last_source',
            field_count       = 'approved_count',
            field_stale       = 'approved_stale',
            field_error       = 'approved_last_error',
        )

    def _sync_one_list(self, config, gdrive_token, list_label, model_name,
                       cache_name, param_sheets_id, param_sheet_name,
                       param_drive_id, param_dbx_token, param_dbx_path,
                       param_sbx_token, param_sbx_path, param_sbx_ns,
                       field_last_sync, field_last_source,
                       field_count, field_stale, field_error):
        """Generic sync for one list. Tries all 4 sources in priority order."""
        sources = [
            ('google_sheets',   lambda: self._fetch_google_sheets(
                config, gdrive_token,
                config.get_param(param_sheets_id, ''),
                config.get_param(param_sheet_name, 'Sheet1'),
            )),
            ('google_drive',    lambda: self._fetch_google_drive(
                config, gdrive_token,
                config.get_param(param_drive_id, ''),
            )),
            ('dropbox',         lambda: self._dropbox_download(
                config.get_param(param_dbx_token, ''),
                config.get_param(param_dbx_path, '/watchlist.csv'),
                namespace_id=None,
            )),
            ('dropbox_sandbox', lambda: self._dropbox_download(
                config.get_param(param_sbx_token, ''),
                config.get_param(param_sbx_path, '/watchlist.csv'),
                namespace_id=config.get_param(param_sbx_ns, '') or None,
            )),
        ]

        raw    = None
        source = None
        for src_name, fetcher in sources:
            try:
                raw = fetcher()
            except Exception as exc:
                _logger.warning('KYC %s: source %s error: %s',
                                list_label, src_name, exc)
                raw = None
            if raw:
                source = src_name
                _logger.info('KYC %s: fetched from %s (%d bytes)',
                             list_label, src_name, len(raw))
                break

        stale = False
        if not raw:
            raw = self._load_named_cache(cache_name)
            if raw:
                source = 'stale_cache'
                stale  = True
                _logger.warning('KYC %s: all live sources failed — stale cache.',
                                list_label)

        if not raw:
            self.write({field_error: 'All sources failed and no cache exists.'})
            _logger.error('KYC %s: unavailable — all sources failed.', list_label)
            return

        try:
            count = self.env[model_name].load_from_csv(raw)
            if not stale:
                self._save_named_cache(cache_name, raw)
            self.write({
                field_last_sync:   fields.Datetime.now(),
                field_last_source: source,
                field_count:       count,
                field_stale:       stale,
                field_error:       False,
            })
            _logger.info('KYC %s sync OK. source=%s entries=%d stale=%s',
                         list_label, source, count, stale)
        except Exception as exc:
            self.write({field_error: str(exc)})
            _logger.error('KYC %s load failed: %s', list_label, exc)

    # ══════════════════════════════════════════════════════════════════════
    # SOURCE 1 — Google Sheets (exports as CSV via Sheets API)
    # Config params:
    #   kyc.gsheets.spreadsheet_id  — the spreadsheet ID from the URL
    #   kyc.gsheets.sheet_name      — sheet/tab name (default: Sheet1)
    # Uses the same service account as Google Drive.
    # ══════════════════════════════════════════════════════════════════════
    def _fetch_google_sheets(self, config, token: Optional[str],
                             spreadsheet_id: str = '',
                             sheet_name: str = 'Sheet1') -> Optional[bytes]:
        if not spreadsheet_id or not token:
            return None
        try:
            # Export sheet as CSV using Google Sheets API
            encoded_sheet = urllib.parse.quote(sheet_name)
            url = (
                f'https://sheets.googleapis.com/v4/spreadsheets/'
                f'{spreadsheet_id}/values/{encoded_sheet}'
                f'?majorDimension=ROWS'
            )
            req = urllib.request.Request(
                url,
                headers={'Authorization': f'Bearer {token}'},
            )
            with urllib.request.urlopen(req, timeout=20) as resp:
                data = json.loads(resp.read())

            rows = data.get('values', [])
            if not rows:
                _logger.warning('KYC: Google Sheets returned empty data.')
                return None

            # Convert rows to CSV bytes
            import csv, io
            buf = io.StringIO()
            writer = csv.writer(buf)
            writer.writerows(rows)
            raw = buf.getvalue().encode('utf-8')
            _logger.info('KYC: Google Sheets export OK (%d rows, %d bytes)',
                         len(rows), len(raw))
            return raw
        except Exception as exc:
            _logger.warning('KYC: Google Sheets fetch failed: %s', exc)
            return None

    # ══════════════════════════════════════════════════════════════════════
    # SOURCE 2 — Google Drive plain CSV file
    # Config params:
    #   kyc.gdrive.file_id  — Drive file ID from the URL
    # ══════════════════════════════════════════════════════════════════════
    def _fetch_google_drive(self, config, token: Optional[str],
                            file_id: str = '') -> Optional[bytes]:
        if not file_id or not token:
            return None
        try:
            url = f'https://www.googleapis.com/drive/v3/files/{file_id}?alt=media'
            req = urllib.request.Request(
                url,
                headers={'Authorization': f'Bearer {token}'},
            )
            with urllib.request.urlopen(req, timeout=20) as resp:
                raw = resp.read()
            _logger.info('KYC: Google Drive CSV download OK (%d bytes)', len(raw))
            return raw
        except Exception as exc:
            _logger.warning('KYC: Google Drive fetch failed: %s', exc)
            return None

    # ══════════════════════════════════════════════════════════════════════
    # SOURCE 3 — Dropbox (standard / personal / team)
    # Config params:
    #   kyc.dropbox.access_token  — long-lived access token
    #   kyc.dropbox.file_path     — path in Dropbox (default: /watchlist.csv)
    # ══════════════════════════════════════════════════════════════════════
    def _fetch_dropbox(self, config) -> Optional[bytes]:
        token     = config.get_param('kyc.dropbox.access_token', '')
        file_path = config.get_param('kyc.dropbox.file_path', '/watchlist.csv')
        if not token:
            return None
        return self._dropbox_download(token, file_path, namespace_id=None)

    # ══════════════════════════════════════════════════════════════════════
    # SOURCE 4 — Dropbox Sandbox (team namespace / sandbox environment)
    # Config params:
    #   kyc.dropbox.sandbox_token      — sandbox app access token
    #   kyc.dropbox.sandbox_file_path  — path inside sandbox (default: /watchlist.csv)
    #   kyc.dropbox.sandbox_namespace  — namespace ID for team sandbox (optional)
    # ══════════════════════════════════════════════════════════════════════
    def _fetch_dropbox_sandbox(self, config) -> Optional[bytes]:
        token      = config.get_param('kyc.dropbox.sandbox_token', '')
        file_path  = config.get_param('kyc.dropbox.sandbox_file_path', '/watchlist.csv')
        namespace  = config.get_param('kyc.dropbox.sandbox_namespace', '')
        if not token:
            return None
        return self._dropbox_download(token, file_path,
                                      namespace_id=namespace or None)

    def _dropbox_download(self, token: str, file_path: str,
                          namespace_id: Optional[str]) -> Optional[bytes]:
        """
        Generic Dropbox file downloader.
        If namespace_id is provided, uses Dropbox-API-Path-Root header
        to access a team namespace / sandbox namespace.
        """
        try:
            url     = 'https://content.dropboxapi.com/2/files/download'
            api_arg = json.dumps({'path': file_path})
            headers = {
                'Authorization':   f'Bearer {token}',
                'Dropbox-API-Arg': api_arg,
            }
            if namespace_id:
                # Route into a specific namespace (team folder / sandbox)
                headers['Dropbox-API-Path-Root'] = json.dumps({
                    '.tag':         'namespace_id',
                    'namespace_id': str(namespace_id),
                })
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=20) as resp:
                raw = resp.read()
            label = f'Dropbox sandbox({namespace_id})' if namespace_id else 'Dropbox'
            _logger.info('KYC: %s download OK (%d bytes)', label, len(raw))
            return raw
        except Exception as exc:
            label = f'Dropbox sandbox({namespace_id})' if namespace_id else 'Dropbox'
            _logger.warning('KYC: %s fetch failed: %s', label, exc)
            return None

    # ══════════════════════════════════════════════════════════════════════
    # Google OAuth2 — JWT service account token (stdlib only)
    # ══════════════════════════════════════════════════════════════════════
    @staticmethod
    def _gdrive_get_token(sa: dict) -> Optional[str]:
        """
        Mint a short-lived OAuth2 bearer token from a service account JSON key.
        Scopes: Drive readonly + Sheets readonly.
        Uses only stdlib: urllib + base64 + json.
        Requires cryptography or rsa package for RSA-SHA256 signing.
        """
        try:
            import time as _time
            import json as _json
            header = base64.urlsafe_b64encode(
                _json.dumps({'alg': 'RS256', 'typ': 'JWT'}).encode()
            ).rstrip(b'=').decode()
            now   = int(_time.time())
            claim = {
                'iss':   sa['client_email'],
                'scope': ' '.join([
                    'https://www.googleapis.com/auth/drive.readonly',
                    'https://www.googleapis.com/auth/spreadsheets.readonly',
                ]),
                'aud': 'https://oauth2.googleapis.com/token',
                'iat': now,
                'exp': now + 3600,
            }
            claim_b64     = base64.urlsafe_b64encode(
                _json.dumps(claim).encode()
            ).rstrip(b'=').decode()
            signing_input = f'{header}.{claim_b64}'.encode()

            try:
                from cryptography.hazmat.primitives import hashes, serialization
                from cryptography.hazmat.primitives.asymmetric import padding
                private_key = serialization.load_pem_private_key(
                    sa['private_key'].encode(), password=None)
                signature = private_key.sign(
                    signing_input, padding.PKCS1v15(), hashes.SHA256())
            except ImportError:
                try:
                    import rsa as _rsa
                    private_key = _rsa.PrivateKey.load_pkcs1(
                        sa['private_key'].encode())
                    signature = _rsa.sign(signing_input, private_key, 'SHA-256')
                except ImportError:
                    _logger.warning(
                        'KYC: No RSA library for Google auth. '
                        'Install: pip install cryptography --break-system-packages')
                    return None

            sig_b64 = base64.urlsafe_b64encode(signature).rstrip(b'=').decode()
            jwt     = f'{header}.{claim_b64}.{sig_b64}'

            data = urllib.parse.urlencode({
                'grant_type': 'urn:ietf:params:oauth:grant-type:jwt-bearer',
                'assertion':  jwt,
            }).encode()
            req = urllib.request.Request(
                'https://oauth2.googleapis.com/token',
                data=data,
                headers={'Content-Type': 'application/x-www-form-urlencoded'},
            )
            with urllib.request.urlopen(req, timeout=15) as resp:
                result = _json.loads(resp.read())
            return result.get('access_token')
        except Exception as exc:
            _logger.warning('KYC: Google token error: %s', exc)
            return None

    # ══════════════════════════════════════════════════════════════════════
    # Cache — ir.attachment (Odoo filestore), keyed by cache_name
    # ══════════════════════════════════════════════════════════════════════
    def _save_named_cache(self, cache_name: str, raw: bytes):
        Att = self.env['ir.attachment'].sudo()
        Att.search([('name', '=', cache_name),
                    ('res_model', '=', 'kyc.watchlist.sync')]).unlink()
        Att.create({
            'name':      cache_name,
            'res_model': 'kyc.watchlist.sync',
            'res_id':    self.id or 0,
            'datas':     base64.b64encode(raw).decode(),
            'mimetype':  'text/csv',
        })

    def _load_named_cache(self, cache_name: str) -> Optional[bytes]:
        att = self.env['ir.attachment'].sudo().search([
            ('name', '=', cache_name),
            ('res_model', '=', 'kyc.watchlist.sync'),
        ], limit=1)
        if att:
            return base64.b64decode(att.datas)
        return None
