# -*- coding: utf-8 -*-
import logging
import re

from odoo import api, fields, models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

# Tokens shorter than this are ignored when scoring description vs rate name.
MIN_TOKEN_LEN = 4
# Minimum overlap to accept an automatic match (otherwise the line is left as-is).
MIN_TOKEN_OVERLAP = 2


class BoqProject(models.Model):
    _inherit = 'ai.boq.project'

    master_rate_match_summary = fields.Text(string='Master Rate Match Summary', readonly=True)

    def action_master_rate_check(self):
        """Re-price each BOQ line using the Buruuj master rate database.

        Strategy per line, in order:
          1. Already linked → use that rate.
          2. Description starts with a known rate code (case-insensitive) → exact-code match.
          3. Token-overlap fuzzy match against rate.name; require a strict winner
             (top score >= MIN_TOKEN_OVERLAP and strictly greater than runner-up).
        Lines with no match keep their existing AI-estimated price.
        """
        self.ensure_one()
        if not self.line_ids:
            raise UserError(_('No BOQ lines to check.'))

        Rate = self.env['buruuj.rate']
        company = self.company_id or self.env.company
        rates = Rate.search([
            ('company_id', '=', company.id),
            ('active', '=', True),
        ])
        if not rates:
            raise UserError(_(
                'No active master rates found for company %s. '
                'Add some in Tendering → Master Rate Database first.'
            ) % company.display_name)

        codes_index = {(r.code or '').strip().upper(): r for r in rates if r.code}
        rate_token_index = self._build_rate_token_index(rates)

        direct = code_hits = fuzzy = unmatched = 0
        deltas = []

        for line in self.line_ids:
            rate = False
            if line.master_rate_id and line.master_rate_id in rates:
                rate = line.master_rate_id
                direct += 1
            else:
                rate = self._find_rate_by_code(line.description, codes_index)
                if rate:
                    code_hits += 1
                else:
                    rate = self._find_rate_by_tokens(line.description, rate_token_index)
                    if rate:
                        fuzzy += 1

            if not rate:
                unmatched += 1
                continue

            old = line.unit_price or 0.0
            new = rate.unit_rate or 0.0
            update = {'master_rate_id': rate.id}
            if new and new > 0:
                update['unit_price'] = new
            if not line.uom_id and rate.uom_id:
                update['uom_id'] = rate.uom_id.id
            line.write(update)

            if old and new and old != new:
                pct = ((new - old) / old) * 100.0
                deltas.append((line.description, old, new, pct))

        total = len(self.line_ids)
        summary = [
            _('• Already linked: %d') % direct,
            _('• Matched by code: %d') % code_hits,
            _('• Matched by description: %d') % fuzzy,
            _('• Unmatched (kept AI estimate): %d') % unmatched,
        ]
        if deltas:
            biggest = sorted(deltas, key=lambda d: abs(d[3]), reverse=True)[:5]
            summary.append(_('\nLargest price corrections:'))
            for desc, old, new, pct in biggest:
                summary.append(_('  - %s: %.2f → %.2f (%+.1f%%)') %
                               ((desc or '')[:60], old, new, pct))

        self.write({'master_rate_match_summary': '\n'.join(summary)})
        self.message_post(body=_(
            'Master-rate cross-check: %(p)d/%(t)d lines priced from <b>%(co)s</b> rates.',
            p=direct + code_hits + fuzzy, t=total, co=company.display_name))
        return {'type': 'ir.actions.client', 'tag': 'reload'}

    @staticmethod
    def _tokens(text):
        if not text:
            return set()
        return {t.lower() for t in re.findall(r'\w+', text) if len(t) >= MIN_TOKEN_LEN}

    def _build_rate_token_index(self, rates):
        return [(r, self._tokens(r.name)) for r in rates if r.name]

    def _find_rate_by_code(self, description, codes_index):
        if not description or not codes_index:
            return False
        # First word/token of the description, normalized.
        m = re.match(r'\s*([A-Za-z0-9\-_/\.]+)', description)
        if not m:
            return False
        token = m.group(1).strip().upper()
        return codes_index.get(token, False)

    def _find_rate_by_tokens(self, description, rate_token_index):
        desc_tokens = self._tokens(description)
        if not desc_tokens:
            return False
        scored = []
        for rate, rate_tokens in rate_token_index:
            if not rate_tokens:
                continue
            overlap = len(desc_tokens & rate_tokens)
            if overlap >= MIN_TOKEN_OVERLAP:
                scored.append((overlap, rate))
        if not scored:
            return False
        scored.sort(key=lambda x: -x[0])
        if len(scored) > 1 and scored[1][0] >= scored[0][0]:
            return False  # ambiguous — refuse to guess
        return scored[0][1]
