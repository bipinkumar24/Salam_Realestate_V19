# -*- coding: utf-8 -*-

import csv, io, re, unicodedata, logging
from odoo import models, fields, api, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class KYCApprovedEntry(models.Model):
    _name        = 'kyc.approved.entry'
    _description = 'KYC Bank Approved List Entry'
    _order       = 'name asc'
    _rec_name    = 'name'

    name          = fields.Char(string='Full Name',       required=True, index=True)
    id_number     = fields.Char(string='ID Number',       index=True)
    nationality   = fields.Char(string='Nationality')
    approved_by   = fields.Char(string='Approved By')
    approval_ref  = fields.Char(string='Approval Reference')
    approval_date = fields.Char(string='Approval Date')
    category      = fields.Char(string='Category',
                                help='e.g. VIP, Corporate, Retail, Embassy')
    notes         = fields.Text(string='Notes')
    active        = fields.Boolean(default=True)
    source_row    = fields.Integer(string='Source Row #', readonly=True)

    _name_unique = models.Constraint(
        ('unique(name, id_number)', 'An approved entry with this name and ID already exists.'),
    )

    # ── Matching helpers (shared with watchlist) ─────────────────────────
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

    @api.model
    def search_name(self, name_query, threshold=0.70):
        """Token-based name search against approved list."""
        qn = self._normalise(name_query)
        qt = self._tokens(qn)
        results = self.env['kyc.approved.entry']
        for entry in self.search([('active', '=', True)]):
            score = self._score(qn, qt, entry.name)
            if score >= threshold:
                results |= entry
        return results

    @api.model
    def search_id(self, id_number):
        """Exact normalised ID match."""
        if not id_number:
            return self.env['kyc.approved.entry']
        norm = self._normalise(id_number)
        return self.search([
            ('active', '=', True),
            ('id_number', '!=', False),
        ]).filtered(lambda e: self._normalise(e.id_number) == norm)

    # ── Bulk load from CSV bytes ─────────────────────────────────────────
    @api.model
    def load_from_csv(self, raw_bytes):
        """
        Replace entire approved list from a CSV.
        Expected columns: name, id_number, nationality, approved_by,
                          approval_ref, approval_date, category, notes
        """
        text    = raw_bytes.decode('utf-8-sig', errors='replace')
        reader  = csv.DictReader(io.StringIO(text))
        entries = []
        for i, row in enumerate(reader, 1):
            r = {k.strip().lower().replace(' ', '_'): (v or '').strip()
                 for k, v in row.items()}
            name = r.get('name') or r.get('full_name', '')
            if not name:
                continue
            entries.append({
                'name':          name,
                'id_number':     r.get('id_number') or r.get('id', ''),
                'nationality':   r.get('nationality', ''),
                'approved_by':   r.get('approved_by', ''),
                'approval_ref':  r.get('approval_ref') or r.get('reference', ''),
                'approval_date': r.get('approval_date') or r.get('date', ''),
                'category':      r.get('category', ''),
                'notes':         r.get('notes', ''),
                'source_row':    i,
            })
        if not entries:
            raise UserError(_('Approved list CSV contained no valid entries '
                              '(missing "name" column?).'))
        self.search([]).unlink()
        self.create(entries)
        _logger.info('KYC approved list loaded: %d entries.', len(entries))
        return len(entries)
