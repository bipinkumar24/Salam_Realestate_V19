# -*- coding: utf-8 -*-
"""BOQ CSV import wizard with optional AI-assisted master-rate alignment."""
import base64
import csv
import io
import json
import re
from difflib import SequenceMatcher

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class BoqImportWizard(models.TransientModel):
    _name = 'buruuj.boq.import.wizard'
    _description = 'Import BOQ from CSV'

    boq_id = fields.Many2one('buruuj.boq', string='Target BOQ', required=True,
                             default=lambda self: self.env.context.get('active_id'))
    csv_file = fields.Binary(string='CSV File', required=True)
    csv_filename = fields.Char(string='Filename')

    auto_align = fields.Boolean(
        string='Fuzzy-match to master rates', default=True,
        help='After import, auto-link each line to the closest matching '
             'master rate by description similarity.')
    match_threshold = fields.Float(
        string='Match threshold', default=0.62,
        help='Similarity score (0.0-1.0) required for an automatic match.')
    use_ai = fields.Boolean(
        string='AI refinement (Anthropic)', default=False,
        help='For lines where fuzzy match was below threshold, ask Claude '
             'to propose matches against the master rate catalog.')
    replace_existing = fields.Boolean(
        string='Replace existing BOQ lines', default=False,
        help='Delete all current lines before importing.')

    rows_imported = fields.Integer(readonly=True)
    rows_matched = fields.Integer(readonly=True)
    rows_ai_matched = fields.Integer(readonly=True)
    rows_unmatched = fields.Integer(readonly=True)
    result_message = fields.Text(readonly=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('done',  'Done'),
    ], default='draft', readonly=True)

    # ---------------------------------------------------------------
    # Public action
    # ---------------------------------------------------------------
    def action_import(self):
        self.ensure_one()
        if not self.csv_file:
            raise UserError(_('Please upload a CSV file.'))

        rows = self._parse_csv()
        if not rows:
            raise UserError(_('CSV is empty or could not be parsed.'))

        if self.replace_existing:
            self.boq_id.line_ids.unlink()
            self.boq_id.section_ids.unlink()

        Section = self.env['buruuj.boq.section']
        Line = self.env['buruuj.boq.line']
        Uom = self.env['uom.uom']
        Trade = self.env['buruuj.trade']

        # Index existing sections by code
        section_by_code = {s.code: s for s in self.boq_id.section_ids}

        # Cache uom and trade lookups
        uom_cache = {}
        trade_cache = {}

        created_lines = self.env['buruuj.boq.line']
        for row in rows:
            sec_code = (row.get('section_code') or '').strip()
            sec_name = (row.get('section_name') or '').strip()
            section = section_by_code.get(sec_code)
            if not section and sec_code:
                section = Section.create({
                    'boq_id': self.boq_id.id,
                    'code': sec_code,
                    'name': sec_name or sec_code,
                })
                section_by_code[sec_code] = section

            uom_name = (row.get('uom') or '').strip()
            uom = uom_cache.get(uom_name)
            if uom_name and not uom:
                uom = Uom.search([('name', '=ilike', uom_name)], limit=1)
                if not uom:
                    uom = Uom.search(
                        [('name', 'ilike', uom_name)], limit=1)
                uom_cache[uom_name] = uom

            trade_name = (row.get('trade') or '').strip()
            trade = trade_cache.get(trade_name)
            if trade_name and not trade:
                trade = Trade.search([('name', '=ilike', trade_name)], limit=1)
                trade_cache[trade_name] = trade

            vals = {
                'boq_id': self.boq_id.id,
                'section_id': section.id if section else False,
                'item_no': (row.get('item_no') or '').strip() or '-',
                'description': (row.get('description') or '').strip(),
                'uom_id': uom.id if uom else False,
                'quantity': self._to_float(row.get('quantity')),
                'unit_rate': self._to_float(row.get('unit_rate')),
                'labor_cost': self._to_float(row.get('labor_cost')),
                'material_cost': self._to_float(row.get('material_cost')),
                'equipment_cost': self._to_float(row.get('equipment_cost')),
                'subcontract_cost': self._to_float(row.get('subcontract_cost')),
                'wastage_percent': self._to_float(row.get('wastage_percent')),
                'trade_id': trade.id if trade else False,
                'notes': (row.get('notes') or '').strip() or False,
            }
            line = Line.create(vals)
            created_lines |= line

        rows_imported = len(created_lines)
        rows_matched = 0
        rows_ai_matched = 0

        # Pass 1: fuzzy match
        if self.auto_align:
            rows_matched = self._fuzzy_align(created_lines)

        # Pass 2: AI refine the unmatched
        if self.use_ai:
            unmatched = created_lines.filtered(lambda l: not l.rate_id)
            rows_ai_matched = self._ai_align(unmatched)

        rows_unmatched = len(created_lines.filtered(lambda l: not l.rate_id))

        msg = (
            f'Imported {rows_imported} line(s).\n'
            f'Fuzzy-matched: {rows_matched}\n'
            f'AI-matched: {rows_ai_matched}\n'
            f'Unmatched: {rows_unmatched}'
        )
        self.write({
            'state': 'done',
            'rows_imported': rows_imported,
            'rows_matched': rows_matched,
            'rows_ai_matched': rows_ai_matched,
            'rows_unmatched': rows_unmatched,
            'result_message': msg,
        })
        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }

    def action_open_boq(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'buruuj.boq',
            'res_id': self.boq_id.id,
            'view_mode': 'form',
            'target': 'current',
        }

    # ---------------------------------------------------------------
    # CSV parsing
    # ---------------------------------------------------------------
    def _parse_csv(self):
        raw = base64.b64decode(self.csv_file)
        for encoding in ('utf-8-sig', 'utf-8', 'latin-1'):
            try:
                text = raw.decode(encoding)
                break
            except UnicodeDecodeError:
                continue
        # Sniff dialect (handles ; vs ,)
        try:
            dialect = csv.Sniffer().sniff(text[:4096], delimiters=',;\t')
        except csv.Error:
            dialect = csv.excel
        reader = csv.DictReader(io.StringIO(text), dialect=dialect)
        rows = []
        for row in reader:
            # Normalize keys to lowercase, strip whitespace
            rows.append({(k or '').strip().lower(): (v or '') for k, v in row.items() if k})
        return rows

    @staticmethod
    def _to_float(value):
        if value is None:
            return 0.0
        s = str(value).strip().replace(',', '')
        if not s:
            return 0.0
        try:
            return float(s)
        except ValueError:
            return 0.0

    # ---------------------------------------------------------------
    # Pass 1: fuzzy match
    # ---------------------------------------------------------------
    def _fuzzy_align(self, lines):
        Rate = self.env['buruuj.rate']
        rates = Rate.search([])
        if not rates:
            return 0
        rate_descriptions = [(r, self._normalize(r.description or r.name or ''))
                             for r in rates]
        matched = 0
        threshold = max(0.0, min(1.0, self.match_threshold or 0.62))
        for line in lines:
            if line.rate_id:
                continue
            target = self._normalize(line.description or '')
            if not target:
                continue
            best = None
            best_score = 0.0
            for rate, desc in rate_descriptions:
                if not desc:
                    continue
                score = SequenceMatcher(None, target, desc).ratio()
                if score > best_score:
                    best, best_score = rate, score
            if best and best_score >= threshold:
                vals = {'rate_id': best.id}
                # only fill unit_rate if line had none
                if not line.unit_rate and best.unit_rate:
                    vals['unit_rate'] = best.unit_rate
                if not line.uom_id and best.uom_id:
                    vals['uom_id'] = best.uom_id.id
                if not line.trade_id and best.trade_id:
                    vals['trade_id'] = best.trade_id.id
                line.write(vals)
                matched += 1
        return matched

    @staticmethod
    def _normalize(s):
        s = (s or '').lower()
        s = re.sub(r'[^\w\s]', ' ', s)
        s = re.sub(r'\s+', ' ', s).strip()
        return s

    # ---------------------------------------------------------------
    # Pass 2: AI alignment via Anthropic
    # ---------------------------------------------------------------
    def _ai_align(self, lines):
        if not lines:
            return 0
        Ai = self.env.get('buruuj.ai.client')
        if Ai is None:
            return 0  # buruuj_ai not installed
        client = Ai
        if hasattr(client, 'is_enabled') and not client.is_enabled():
            return 0

        Rate = self.env['buruuj.rate']
        rates = Rate.search([])
        if not rates:
            return 0
        # Build catalog (cap at 200 to keep prompt size sane)
        catalog = []
        for r in rates[:200]:
            catalog.append({
                'code': r.name or f'RATE-{r.id}',
                'description': (r.description or r.name or '')[:200],
                'uom': r.uom_id.name if r.uom_id else '',
            })

        # Build items batch
        items = []
        line_by_index = {}
        for i, line in enumerate(lines):
            items.append({
                'index': i,
                'description': (line.description or '')[:300],
                'uom': line.uom_id.name if line.uom_id else '',
            })
            line_by_index[i] = line

        system = (
            "You are a construction estimator helping match BOQ items to "
            "master-rate catalog entries. For each BOQ item, decide whether "
            "any catalog entry is a confident match by description and UoM. "
            "Reply with a JSON array only, no commentary. "
            'Format: [{"index": 0, "rate_code": "CON-C30", "confidence": "high"}]. '
            'Use "rate_code": null when no good match exists. Confidence values: '
            '"high", "medium", "low".'
        )
        user_text = (
            "BOQ items to match:\n"
            + json.dumps(items, ensure_ascii=False)
            + "\n\nMaster rate catalog:\n"
            + json.dumps(catalog, ensure_ascii=False)
        )
        try:
            res = client.complete(
                system=system,
                messages=[{"role": "user", "content": user_text}],
                task_type='boq_align',
                task_record=('buruuj.boq', self.boq_id.id),
            )
        except Exception:
            return 0
        text = (res or {}).get('text', '') or ''
        match = re.search(r'\[[\s\S]*\]', text)
        if not match:
            return 0
        try:
            decisions = json.loads(match.group(0))
        except Exception:
            return 0

        rates_by_code = {r.name: r for r in rates if r.name}
        applied = 0
        for d in decisions:
            if not isinstance(d, dict):
                continue
            idx = d.get('index')
            code = d.get('rate_code')
            conf = (d.get('confidence') or '').lower()
            if idx is None or not code or conf == 'low':
                continue
            line = line_by_index.get(idx)
            rate = rates_by_code.get(code)
            if not line or not rate:
                continue
            vals = {'rate_id': rate.id}
            if not line.unit_rate and rate.unit_rate:
                vals['unit_rate'] = rate.unit_rate
            if not line.uom_id and rate.uom_id:
                vals['uom_id'] = rate.uom_id.id
            if not line.trade_id and rate.trade_id:
                vals['trade_id'] = rate.trade_id.id
            line.write(vals)
            applied += 1
        return applied