# -*- coding: utf-8 -*-
import csv
import io
import unicodedata
import re
import logging
from odoo import models, fields, api, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class KYCWatchlistEntry(models.Model):
    """
    Single watchlist entry stored in Odoo database.
    Populated by the sync engine from Google Drive or Dropbox CSV.
    """
    _name = 'kyc.watchlist.entry'
    _description = 'KYC Watchlist Entry'
    _order = 'name asc'
    _rec_name = 'name'

    name = fields.Char(string='Full Name', required=True, index=True)
    id_number = fields.Char(string='ID Number', index=True)
    nationality = fields.Char(string='Nationality')
    date_of_birth = fields.Char(string='Date of Birth')
    list_name = fields.Char(string='List / Source', default='Watchlist')
    reason = fields.Char(string='Designation / Reason')
    active = fields.Boolean(default=True)
    source_row = fields.Integer(string='Source Row #', readonly=True)

    _name_unique = models.Constraint(
        ('unique(name, id_number)', 'A watchlist entry with this name and ID already exists.'),
    )

    @api.model
    def search_name(self, name_query, threshold=0.70):
        """
        Token-based name search. Returns recordset of entries whose
        normalised name scores >= threshold against name_query.
        Also returns exact ID matches regardless of threshold.
        """
        qn = self._normalise(name_query)
        qt = self._tokens(qn)
        results = self.env['kyc.watchlist.entry']
        for entry in self.search([('active', '=', True)]):
            score = self._score(qn, qt, entry.name)
            if score >= threshold:
                results |= entry
        return results

    @api.model
    def search_id(self, id_number):
        """Exact normalised ID match."""
        if not id_number:
            return self.env['kyc.watchlist.entry']
        norm = self._normalise(id_number)
        return self.search([
            ('active', '=', True),
            ('id_number', '!=', False),
        ]).filtered(lambda e: self._normalise(e.id_number) == norm)

    # ── Matching helpers ─────────────────────────────────────────────────
    @staticmethod
    def _normalise(text):
        if not text:
            return ''
        text = unicodedata.normalize('NFKD', text)
        text = ''.join(c for c in text if not unicodedata.combining(c))
        return re.sub(r'\s+', ' ', text.lower().strip())

    @staticmethod
    def _tokens(normalised):
        return {t for t in normalised.split() if len(t) > 1}

    @classmethod
    def _score(cls, qn, qt, candidate):
        cn = cls._normalise(candidate)
        if qn == cn:
            return 1.0
        ct = cls._tokens(cn)
        if not qt or not ct:
            return 0.0
        overlap = len(qt & ct)
        return round(overlap / max(len(qt), len(ct)), 3)

    # ── Bulk load from CSV bytes ─────────────────────────────────────────
    @api.model
    def load_from_csv(self, raw_bytes):
        """
        Replace entire watchlist from a CSV.
        Expected columns: name, id_number, nationality, date_of_birth, list_name, reason
        Returns (added, skipped) counts.
        """
        text = raw_bytes.decode('utf-8-sig', errors='replace')
        reader = csv.DictReader(io.StringIO(text))

        entries = []
        for i, row in enumerate(reader, 1):
            r = {k.strip().lower().replace(' ', '_'): (v or '').strip()
                 for k, v in row.items()}
            name = r.get('name') or r.get('full_name', '')
            if not name:
                continue
            entries.append({
                'name':         name,
                'id_number':    r.get('id_number') or r.get('id', ''),
                'nationality':  r.get('nationality', ''),
                'date_of_birth': r.get('date_of_birth', ''),
                'list_name':    r.get('list_name') or r.get('list', 'Watchlist'),
                'reason':       r.get('reason') or r.get('designation', ''),
                'source_row':   i,
            })

        if not entries:
            raise UserError(_('CSV contained no valid entries (missing "name" column?).'))

        # Wipe and reload
        self.search([]).unlink()
        self.create(entries)
        _logger.info('KYC watchlist loaded: %d entries.', len(entries))
        return len(entries)
