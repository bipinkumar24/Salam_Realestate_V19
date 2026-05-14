# -*- coding: utf-8 -*-
import json
import logging
import urllib.request
import urllib.error
from odoo import models, fields, api, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class BREApplication(models.Model):
    """
    Dual-list KYC screening against:
      LIST 1 — kyc.watchlist.entry  (sanctions/AML/default)
      LIST 2 — kyc.approved.entry   (bank pre-approved clients)

    Outcome:
      watchlist hit            → hit  (always overrides)
      no hit + approved match  → pre_approved
      no hit + no match        → cleared
    """
    _inherit = 'bre.customer.application'

    kyc_status = fields.Selection([
        ('pending',      'Pending'),
        ('cleared',      'Cleared'),
        ('pre_approved', 'Pre-Approved — Bank Approved List'),
        ('hit',          'Hit — Review Required'),
        ('error',        'Error'),
    ], string='KYC Status', default='pending', tracking=True)

    kyc_last_run       = fields.Datetime(string='Last Screening Date', readonly=True)
    kyc_reference      = fields.Char(string='Screening Reference',    readonly=True)
    kyc_result_summary = fields.Text(string='Screening Result',       readonly=True)

    def action_run_kyc_screening(self):
        self.ensure_one()
        self._do_kyc_screening()

    def _do_kyc_screening(self):
        import uuid
        import time as _time

        config    = self.env['ir.config_parameter'].sudo()
        threshold = float(config.get_param('kyc.match.threshold', '0.70'))
        ref       = 'KYC-' + uuid.uuid4().hex[:8].upper()
        t0        = _time.time()

        full_name   = (self.partner_id.name or '').strip()
        id_number   = (self.id_number or '').strip() if hasattr(self, 'id_number') else ''
        nationality = (
            self.nationality_id.name
            if hasattr(self, 'nationality_id') and self.nationality_id else ''
        )

        if not full_name:
            self._kyc_log_error('Applicant has no name — cannot screen.')
            return

        Watchlist = self.env['kyc.watchlist.entry']
        Approved  = self.env['kyc.approved.entry']

        # LIST 1: Watchlist (sanctions)
        wl_id_hits   = Watchlist.search_id(id_number) if id_number else \
                       self.env['kyc.watchlist.entry']
        wl_name_hits = Watchlist.search_name(full_name, threshold=threshold)
        wl_hits      = wl_id_hits | wl_name_hits

        # LIST 2: Approved list
        ap_id_hits   = Approved.search_id(id_number) if id_number else \
                       self.env['kyc.approved.entry']
        ap_name_hits = Approved.search_name(full_name, threshold=threshold)
        ap_hits      = ap_id_hits | ap_name_hits

        elapsed_ms = round((_time.time() - t0) * 1000)

        # Outcome matrix — watchlist hit always wins
        if wl_hits:
            kyc_status = 'hit'
        elif ap_hits:
            kyc_status = 'pre_approved'
        else:
            kyc_status = 'cleared'

        icon_map = {
            'cleared':     '\u2705',
            'pre_approved':'\U0001f7e2',
            'hit':         '\u26a0\ufe0f',
        }
        icon = icon_map[kyc_status]

        wl_total = Watchlist.search_count([('active', '=', True)])
        ap_total = Approved.search_count([('active', '=', True)])

        def _match_label(entry, id_hits, Model, name):
            if entry in id_hits:
                return 'ID exact'
            score = Model._score(
                Model._normalise(name),
                Model._tokens(Model._normalise(name)),
                entry.name,
            )
            return 'name %d%%' % round(score * 100)

        # Build watchlist HTML
        wl_html = ''
        if wl_hits:
            rows = ''.join(
                '<li><b>%s</b> | ID: %s | List: %s | Reason: %s'
                ' <span style="color:grey;font-size:11px">(%s)</span></li>' % (
                    e.name,
                    e.id_number or 'N/A',
                    e.list_name or 'Watchlist',
                    e.reason    or '-',
                    _match_label(e, wl_id_hits, Watchlist, full_name),
                )
                for e in wl_hits
            )
            wl_html = '<b>Watchlist Hits (%d):</b><ul>%s</ul>' % (len(wl_hits), rows)

        # Build approved list HTML
        ap_html = ''
        if ap_hits:
            rows = ''.join(
                '<li><b>%s</b> | ID: %s | Approved by: %s | Ref: %s | Category: %s'
                ' <span style="color:grey;font-size:11px">(%s)</span></li>' % (
                    e.name,
                    e.id_number    or 'N/A',
                    e.approved_by  or '-',
                    e.approval_ref or '-',
                    e.category     or '-',
                    _match_label(e, ap_id_hits, Approved, full_name),
                )
                for e in ap_hits
            )
            ap_html = '<b>Approved List Matches (%d):</b><ul>%s</ul>' % (len(ap_hits), rows)

        verdict_map = {
            'cleared':
                'No matches on either list — applicant is clear.',
            'pre_approved':
                'Found on Bank Approved List — no sanctions hit.',
            'hit':
                'WATCHLIST HIT — officer review required. '
                'Do NOT proceed without compliance sign-off.',
        }

        summary_lines = [
            'Screened: %s | ID: %s | Nationality: %s' % (
                full_name, id_number or 'N/A', nationality or 'N/A'),
            'Result: %s | Threshold: %d%%' % (
                kyc_status.upper().replace('_', ' '), round(threshold * 100)),
            'Watchlist: %d hits (of %d entries) | Approved: %d matches (of %d entries)' % (
                len(wl_hits), wl_total, len(ap_hits), ap_total),
            'Elapsed: %dms | Reference: %s' % (elapsed_ms, ref),
            'Screened by: %s' % self.env.user.name,
        ]
        summary_text = '\n'.join(summary_lines)

        body = (
            '<b>%s KYC DUAL-LIST SCREENING — %s</b><br/>'
            '<b>Screened:</b> %s | ID: %s | Nationality: %s<br/>'
            '<b>Reference:</b> %s<br/>'
            '<b>Verdict:</b> %s<br/>'
            '<b>Watchlist:</b> %d entries | <b>Approved List:</b> %d entries | '
            '<b>Elapsed:</b> %dms<br/>'
            '%s%s'
            '<i>Screened by: %s</i>'
        ) % (
            icon, kyc_status.upper().replace('_', ' '),
            full_name, id_number or 'N/A', nationality or 'N/A',
            ref,
            verdict_map[kyc_status],
            wl_total, ap_total, elapsed_ms,
            wl_html, ap_html,
            self.env.user.name,
        )

        self.write({
            'kyc_status':         kyc_status,
            'kyc_last_run':       fields.Datetime.now(),
            'kyc_reference':      ref,
            'kyc_result_summary': summary_text,
        })
        self.message_post(body=body, subtype_xmlid='mail.mt_note')

    def _kyc_log_error(self, message):
        self.write({
            'kyc_status':         'error',
            'kyc_last_run':       fields.Datetime.now(),
            'kyc_result_summary': message,
        })
        self.message_post(
            body='<b>KYC SCREENING ERROR</b><br/>%s' % message,
            subtype_xmlid='mail.mt_note',
        )
        _logger.error('KYC error on %s: %s', self.name, message)


class InvestmentAppraisal(models.Model):
    """Extend Five Cs Appraisal with KYC fields."""
    _inherit = 'property.investment.application'

    kyc_status = fields.Selection(
        related='bre_application_id.kyc_status',
        string='KYC Status', store=True, readonly=True,
    )
    kyc_last_run = fields.Datetime(
        related='bre_application_id.kyc_last_run',
        string='Last Screening Date', readonly=True,
    )
    kyc_result_summary = fields.Text(
        related='bre_application_id.kyc_result_summary',
        string='Screening Result', readonly=True,
    )

    def action_run_kyc_screening(self):
        self.ensure_one()
        if not self.bre_application_id:
            raise UserError(_('No linked BRE application found.'))
        self.bre_application_id._do_kyc_screening()


class ResConfigSettings(models.TransientModel):
    """KYC configuration in Odoo Settings."""
    _inherit = 'res.config.settings'

    # ── Google shared ─────────────────────────────────────────────────
    kyc_gdrive_sa_path = fields.Char(
        string='Service Account JSON Path',
        config_parameter='kyc.gdrive.service_account_path',
        help='Absolute path to Google service account JSON key on the Odoo server.\n'
             'Example: /etc/odoo/gdrive_kyc_sa.json\n'
             'Used for both Google Sheets and Google Drive sources.',
    )
    # ── Google Sheets (Source 1 — primary) ───────────────────────────
    kyc_gsheets_spreadsheet_id = fields.Char(
        string='Google Sheets Spreadsheet ID',
        config_parameter='kyc.gsheets.spreadsheet_id',
        help='Spreadsheet ID from the URL:\n'
             'https://docs.google.com/spreadsheets/d/SPREADSHEET_ID/edit',
    )
    kyc_gsheets_sheet_name = fields.Char(
        string='Sheet / Tab Name',
        config_parameter='kyc.gsheets.sheet_name',
        default='Sheet1',
        help='Name of the sheet tab containing watchlist data. Default: Sheet1',
    )
    # ── Google Drive CSV (Source 2 — fallback) ───────────────────────
    kyc_gdrive_file_id = fields.Char(
        string='Google Drive CSV File ID',
        config_parameter='kyc.gdrive.file_id',
        help='File ID of a plain CSV on Google Drive (fallback).\n'
             'From URL: https://drive.google.com/file/d/FILE_ID/view',
    )
    # ── Dropbox standard (Source 3) ──────────────────────────────────
    kyc_dropbox_token = fields.Char(
        string='Dropbox Access Token',
        config_parameter='kyc.dropbox.access_token',
    )
    kyc_dropbox_path = fields.Char(
        string='Dropbox File Path',
        config_parameter='kyc.dropbox.file_path',
        default='/watchlist.csv',
    )
    # ── Dropbox Sandbox (Source 4) ───────────────────────────────────
    kyc_dropbox_sandbox_token = fields.Char(
        string='Dropbox Sandbox Access Token',
        config_parameter='kyc.dropbox.sandbox_token',
        help='Access token for the Dropbox sandbox/test environment.',
    )
    kyc_dropbox_sandbox_path = fields.Char(
        string='Dropbox Sandbox File Path',
        config_parameter='kyc.dropbox.sandbox_file_path',
        default='/watchlist.csv',
    )
    kyc_dropbox_sandbox_namespace = fields.Char(
        string='Dropbox Namespace ID (optional)',
        config_parameter='kyc.dropbox.sandbox_namespace',
        help='Team namespace ID for Dropbox team/sandbox. Leave blank for personal.',
    )
    # ── Approved List — Google Sheets ────────────────────────────────
    kyc_approved_gsheets_id = fields.Char(
        string='Approved List Spreadsheet ID',
        config_parameter='kyc.approved.gsheets.spreadsheet_id',
        help='Google Sheets spreadsheet ID for the Bank Approved List.',
    )
    kyc_approved_gsheets_sheet = fields.Char(
        string='Approved List Sheet / Tab Name',
        config_parameter='kyc.approved.gsheets.sheet_name',
        default='Sheet1',
    )
    # ── Approved List — Google Drive CSV ─────────────────────────────
    kyc_approved_gdrive_id = fields.Char(
        string='Approved List Drive File ID',
        config_parameter='kyc.approved.gdrive.file_id',
    )
    # ── Approved List — Dropbox ───────────────────────────────────────
    kyc_approved_dropbox_token = fields.Char(
        string='Approved List Dropbox Token',
        config_parameter='kyc.approved.dropbox.access_token',
    )
    kyc_approved_dropbox_path = fields.Char(
        string='Approved List Dropbox Path',
        config_parameter='kyc.approved.dropbox.file_path',
        default='/approved_list.csv',
    )
    # ── Approved List — Dropbox Sandbox ──────────────────────────────
    kyc_approved_sbx_token = fields.Char(
        string='Approved List Sandbox Token',
        config_parameter='kyc.approved.dropbox.sandbox_token',
    )
    kyc_approved_sbx_path = fields.Char(
        string='Approved List Sandbox Path',
        config_parameter='kyc.approved.dropbox.sandbox_file_path',
        default='/approved_list.csv',
    )
    kyc_approved_sbx_ns = fields.Char(
        string='Approved List Namespace ID',
        config_parameter='kyc.approved.dropbox.sandbox_namespace',
    )
    # ── Matching ─────────────────────────────────────────────────────
    kyc_match_threshold = fields.Float(
        string='Name Match Threshold (0.0–1.0)',
        config_parameter='kyc.match.threshold',
        default=0.7,
    )
