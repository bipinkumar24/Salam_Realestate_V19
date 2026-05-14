# -*- coding: utf-8 -*-
import json
import logging
from odoo import models, fields, api, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

# Optional dependency: OCA queue_job. If installed, action_analyze can dispatch
# the AI call to a worker. If absent, we fall back to synchronous execution.
try:
    from odoo.addons.queue_job.job import job  # type: ignore
    HAS_QUEUE_JOB = True
except ImportError:  # pragma: no cover
    HAS_QUEUE_JOB = False

    def job(*dargs, **dkwargs):
        """No-op decorator when queue_job is not installed."""
        if len(dargs) == 1 and callable(dargs[0]) and not dkwargs:
            return dargs[0]

        def _wrap(func):
            return func
        return _wrap


class BoqProject(models.Model):
    _name = 'ai.boq.project'
    _description = 'AI BOQ Project'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    name = fields.Char(required=True, default=lambda s: _('New'), tracking=True, copy=False)
    partner_id = fields.Many2one('res.partner', string='Customer', tracking=True)
    project_id = fields.Many2one('project.project', string='Project')
    user_id = fields.Many2one('res.users', string='Responsible', default=lambda s: s.env.user, tracking=True)
    company_id = fields.Many2one('res.company', default=lambda s: s.env.company, required=True)
    currency_id = fields.Many2one(related='company_id.currency_id', store=True, readonly=True)

    # Design upload
    design_file = fields.Binary(string='Design File', attachment=True)
    design_filename = fields.Char(string='Design Filename')
    design_preview = fields.Image(string='Preview', max_width=1024, max_height=1024)

    # State
    state = fields.Selection([
        ('draft', 'Draft'),
        ('analyzing', 'Analysing'),
        ('reviewed', 'Reviewed'),
        ('approved', 'Approved'),
        ('cancelled', 'Cancelled'),
    ], default='draft', tracking=True, required=True, copy=False)

    # Lines
    line_ids = fields.One2many('ai.boq.line', 'boq_id', string='BOQ Lines', copy=True)
    total_amount = fields.Monetary(compute='_compute_total_amount', store=True, currency_field='currency_id')
    line_count = fields.Integer(compute='_compute_total_amount', store=True)
    average_confidence = fields.Float(compute='_compute_total_amount', store=True, aggregator='avg')

    # AI metadata
    ai_provider = fields.Char(readonly=True)
    ai_model_used = fields.Char(readonly=True)
    ai_raw_response = fields.Text(readonly=True)
    ai_warnings = fields.Text(readonly=True)
    ai_scale_detected = fields.Char(readonly=True)
    ai_summary = fields.Text(readonly=True)
    analyzed_on = fields.Datetime(readonly=True)
    pages_analyzed = fields.Integer(readonly=True)

    # Linked docs
    sale_order_id = fields.Many2one('sale.order', string='Sales Order', readonly=True, copy=False)

    notes = fields.Html()
    template_id = fields.Many2one('ai.boq.template', string='Apply Template')

    # Price-list cross-check
    pricelist_id = fields.Many2one(
        'product.pricelist', string='Pricelist',
        help="If set, every BOQ line is cross-checked against this pricelist after AI analysis. "
             "Lines linked to a product get the pricelist price applied; lines without a product "
             "are matched by description (best-effort fuzzy lookup).")
    price_check_state = fields.Selection([
        ('not_run', 'Not run'),
        ('matched', 'All matched'),
        ('partial', 'Partial match'),
        ('failed', 'Failed'),
    ], default='not_run', readonly=True, copy=False)
    price_check_summary = fields.Text(readonly=True, copy=False)

    # Async / queue_job
    use_async = fields.Boolean(
        string='Run Async',
        compute='_compute_use_async', store=False,
        help="When queue_job is installed, analysis is dispatched to a worker.")
    job_uuid = fields.Char(readonly=True, copy=False, help="queue_job UUID of the running analysis, if any.")

    # ------------------------------------------------------------------ #
    # Computes
    # ------------------------------------------------------------------ #
    @api.depends('line_ids.subtotal', 'line_ids.confidence_score')
    def _compute_total_amount(self):
        for rec in self:
            rec.total_amount = sum(rec.line_ids.mapped('subtotal'))
            rec.line_count = len(rec.line_ids)
            scores = rec.line_ids.mapped('confidence_score')
            rec.average_confidence = (sum(scores) / len(scores)) if scores else 0.0

    # ------------------------------------------------------------------ #
    # CRUD
    # ------------------------------------------------------------------ #
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('ai.boq.project') or _('New')
        return super().create(vals_list)

    # ------------------------------------------------------------------ #
    # Onchange
    # ------------------------------------------------------------------ #
    @api.onchange('template_id')
    def _onchange_template_id(self):
        if not self.template_id:
            return
        # append template lines
        existing = self.line_ids
        new_lines = [(0, 0, {
            'sequence': tl.sequence,
            'category': tl.category,
            'description': tl.description,
            'product_id': tl.product_id.id,
            'uom_id': tl.uom_id.id,
            'quantity': tl.default_quantity,
            'unit_price': tl.default_unit_price,
            'confidence_score': 1.0,
            'source_reference': _('From template: %s') % self.template_id.name,
        }) for tl in self.template_id.line_ids]
        self.line_ids = [(4, l.id) for l in existing] + new_lines

    # ------------------------------------------------------------------ #
    # Workflow buttons
    # ------------------------------------------------------------------ #
    def _compute_use_async(self):
        """Whether async dispatch is available (queue_job installed AND enabled in settings)."""
        ICP = self.env['ir.config_parameter'].sudo()
        enabled = ICP.get_param('ai_boq.use_queue_job', default='False') == 'True'
        for rec in self:
            rec.use_async = HAS_QUEUE_JOB and enabled

    def action_analyze(self):
        """Entry point. Dispatches to queue_job if available and enabled, otherwise runs inline."""
        self.ensure_one()
        if not self.design_file:
            raise UserError(_("Please upload a design file first."))
        if self.state not in ('draft', 'reviewed'):
            raise UserError(_("Cannot analyse a BOQ in state '%s'.") % self.state)

        self.write({'state': 'analyzing'})
        # set preview from the binary if image
        if (self.design_filename or '').lower().endswith(('.png', '.jpg', '.jpeg')):
            self.design_preview = self.design_file

        if self.use_async:
            description = _("AI analysis: %s") % self.name
            new_self = self.with_delay(description=description) if hasattr(self, 'with_delay') else self
            if hasattr(new_self, 'with_delay'):
                # queue_job present
                job_rec = new_self.with_delay(description=description)._run_analysis()
                self.job_uuid = getattr(job_rec, 'uuid', False) or False
                self.message_post(body=_("Analysis queued (job %s)") % (self.job_uuid or '?'))
                return True
            # fall through if helper missing for any reason
        return self._run_analysis()

    @job(default_channel='root.ai_boq')
    def _run_analysis(self):
        """The actual blocking AI call. Decorated with @job so queue_job can pick it up."""
        self.ensure_one()
        try:
            service = self.env['ai.boq.service']
            data = service.analyze_design(self.design_file, self.design_filename or 'design.pdf')
        except Exception as e:
            self.write({'state': 'draft', 'job_uuid': False})
            self.message_post(body=_("AI analysis failed: %s") % e)
            raise

        self._apply_ai_result(data)
        self.message_post(body=_("AI analysis completed. %d lines extracted.") % len(self.line_ids))
        return True

    def _apply_ai_result(self, data):
        """Translate the AI JSON dict into BOQ lines and metadata."""
        self.ensure_one()
        meta = data.get('_meta', {})
        items = data.get('items') or []
        warnings = data.get('warnings') or []

        # purge previous AI-generated lines (keep manual ones with confidence == 1.0 from template)
        ai_lines = self.line_ids.filtered(lambda l: l.confidence_score < 1.0)
        ai_lines.unlink()

        uom_unit = self.env.ref('uom.product_uom_unit', raise_if_not_found=False)
        line_vals = []
        for idx, item in enumerate(items, start=1):
            uom = self._resolve_uom(item.get('uom')) or uom_unit
            line_vals.append((0, 0, {
                'sequence': idx * 10,
                'category': item.get('category') if item.get('category') in
                            dict(self.env['ai.boq.line']._fields['category'].selection) else 'other',
                'description': (item.get('description') or '').strip()[:255] or _('Unnamed item'),
                'uom_id': uom.id if uom else False,
                'quantity': float(item.get('quantity') or 0.0),
                'unit_price': float(item.get('unit_price_estimate') or 0.0),
                'confidence_score': max(0.0, min(1.0, float(item.get('confidence') or 0.0))),
                'source_reference': item.get('source_reference') or '',
            }))

        self.write({
            'line_ids': line_vals,
            'state': 'reviewed',
            'analyzed_on': fields.Datetime.now(),
            'ai_provider': meta.get('provider'),
            'ai_model_used': meta.get('model'),
            'pages_analyzed': meta.get('pages', 0),
            'ai_raw_response': meta.get('raw_response'),
            'ai_warnings': '\n'.join('• %s' % w for w in warnings) if warnings else False,
            'ai_scale_detected': data.get('scale_detected'),
            'ai_summary': data.get('project_summary'),
            'job_uuid': False,
        })

        # Auto cross-check against pricelist if one is configured
        if self.pricelist_id:
            try:
                self.action_pricelist_check()
            except Exception as e:
                _logger.warning("BOQ price-check failed for %s: %s", self.name, e)
                self.message_post(body=_("Price-list cross-check failed: %s") % e)

    # ------------------------------------------------------------------ #
    # Pricelist cross-check
    # ------------------------------------------------------------------ #
    def action_pricelist_check(self):
        """Cross-check every BOQ line against the configured pricelist.

        For lines linked to a product, fetch the pricelist price for that product.
        For lines without a product, attempt a fuzzy name lookup; if a single
        product matches with high confidence, link it and apply the price.
        Otherwise, the line is left untouched but flagged in the summary.
        """
        self.ensure_one()
        if not self.pricelist_id:
            raise UserError(_("Set a Pricelist on the BOQ first."))
        if not self.line_ids:
            raise UserError(_("No BOQ lines to check."))

        Product = self.env['product.product']
        pricelist = self.pricelist_id

        matched, fuzzy_matched, unmatched, deltas = 0, 0, 0, []

        for line in self.line_ids:
            product = line.product_id
            if not product:
                # fuzzy match by description against product name / default_code
                desc = (line.description or '').strip()
                if not desc:
                    unmatched += 1
                    continue
                product = self._fuzzy_find_product(desc)
                if product:
                    line.product_id = product.id
                    fuzzy_matched += 1
                else:
                    unmatched += 1
                    continue
            else:
                matched += 1

            # _get_product_price has been the stable API since v15; in v19 it remains
            # on product.pricelist and accepts (product, quantity, **kwargs).
            try:
                qty = max(line.quantity or 1.0, 1.0)
                pl_price = pricelist._get_product_price(product, qty)
            except Exception:
                # Fallback to list_price if the pricelist API misbehaves
                pl_price = product.lst_price

            if pl_price and pl_price > 0:
                old = line.unit_price or 0.0
                line.unit_price = pl_price
                if old:
                    pct = ((pl_price - old) / old) * 100.0
                    deltas.append((line.description, old, pl_price, pct))

        # Build summary
        total = len(self.line_ids)
        lines_summary = [
            _("• Direct product matches: %d") % matched,
            _("• Fuzzy matches by description: %d") % fuzzy_matched,
            _("• Unmatched (kept AI estimate): %d") % unmatched,
        ]
        if deltas:
            big_swings = sorted(deltas, key=lambda d: abs(d[3]), reverse=True)[:5]
            lines_summary.append(_("\nLargest price corrections:"))
            for desc, old, new, pct in big_swings:
                lines_summary.append(_("  - %s: %.2f → %.2f (%+.1f%%)") % (desc[:60], old, new, pct))

        if unmatched == 0:
            state = 'matched'
        elif (matched + fuzzy_matched) > 0:
            state = 'partial'
        else:
            state = 'failed'

        self.write({
            'price_check_state': state,
            'price_check_summary': '\n'.join(lines_summary),
        })
        self.message_post(body=_("Pricelist cross-check: %d/%d lines priced from <b>%s</b>.") %
                          (matched + fuzzy_matched, total, pricelist.display_name))
        return True

    def _fuzzy_find_product(self, description):
        """Best-effort: split the description into significant tokens and look for
        a product whose name contains all of them. Returns a single product or False.

        Deliberately conservative — we only return a match if exactly one product
        scores highly, to avoid silently linking the wrong item.
        """
        Product = self.env['product.product']
        # tokens: words >= 4 chars, lowercased
        tokens = [t for t in description.lower().replace(',', ' ').replace('/', ' ').split()
                  if len(t) >= 4]
        if not tokens:
            return False

        # First pass: strict — all tokens must appear in name
        domain = [('sale_ok', '=', True)] + [('name', 'ilike', t) for t in tokens]
        matches = Product.search(domain, limit=5)
        if len(matches) == 1:
            return matches
        if len(matches) > 1:
            # ambiguous — refuse to guess
            return False

        # Second pass: relax to first 2 tokens
        if len(tokens) >= 2:
            domain = [('sale_ok', '=', True), ('name', 'ilike', tokens[0]), ('name', 'ilike', tokens[1])]
            matches = Product.search(domain, limit=2)
            if len(matches) == 1:
                return matches
        return False

    # ------------------------------------------------------------------ #
    # UoM resolution
    # ------------------------------------------------------------------ #
    def _resolve_uom(self, uom_str):
        """Best-effort match of an AI-supplied UoM string to an Odoo uom.uom."""
        if not uom_str:
            return self.env['uom.uom']
        s = uom_str.strip().lower()
        mapping = {
            'm': 'Units',  # fallback; many DBs lack metric units OOTB
            'm2': 'Units', 'sqm': 'Units', 'm²': 'Units',
            'm3': 'Units', 'cum': 'Units', 'm³': 'Units',
            'kg': 'kg', 'kgs': 'kg',
            'ton': 't', 't': 't', 'tonne': 't',
            'nos': 'Units', 'no': 'Units', 'pcs': 'Units', 'each': 'Units',
            'lot': 'Units', 'ls': 'Units',
        }
        target_name = mapping.get(s)
        if not target_name:
            # try literal match
            uom = self.env['uom.uom'].search([('name', '=ilike', uom_str)], limit=1)
            return uom
        return self.env['uom.uom'].search([('name', '=', target_name)], limit=1)

    def action_approve(self):
        for rec in self:
            if rec.state != 'reviewed':
                raise UserError(_("Only reviewed BOQs can be approved."))
            if not rec.line_ids:
                raise UserError(_("Cannot approve an empty BOQ."))
            rec.state = 'approved'
            rec.message_post(body=_("BOQ approved by %s") % self.env.user.name)

    def action_reset_to_draft(self):
        self.write({'state': 'draft'})

    def action_cancel(self):
        self.write({'state': 'cancelled'})

    def action_create_sale_order(self):
        self.ensure_one()
        if self.state != 'approved':
            raise UserError(_("Approve the BOQ first."))
        if not self.partner_id:
            raise UserError(_("Set a customer to create a sales order."))
        if self.sale_order_id:
            return self._open_record(self.sale_order_id)

        SO = self.env['sale.order']
        order_lines = []
        for line in self.line_ids:
            order_lines.append((0, 0, {
                'name': '[%s] %s' % (dict(line._fields['category'].selection).get(line.category, ''), line.description),
                'product_id': line.product_id.id if line.product_id else False,
                'product_uom_qty': line.quantity,
                'product_uom': line.uom_id.id if line.uom_id else False,
                'price_unit': line.unit_price,
            }))
        if not order_lines:
            raise UserError(_("No lines to convert."))

        # Some Odoo variants require a product on each SO line; create a generic service product if missing.
        generic = self._get_or_create_generic_product()
        for ol in order_lines:
            if not ol[2].get('product_id'):
                ol[2]['product_id'] = generic.id
                if not ol[2].get('product_uom'):
                    ol[2]['product_uom'] = generic.uom_id.id

        so = SO.create({
            'partner_id': self.partner_id.id,
            'origin': self.name,
            'order_line': order_lines,
        })
        self.sale_order_id = so.id
        return self._open_record(so)

    def _get_or_create_generic_product(self):
        Product = self.env['product.product']
        prod = Product.search([('default_code', '=', 'BOQ-GEN')], limit=1)
        if prod:
            return prod
        return Product.create({
            'name': 'BOQ Generic Item',
            'default_code': 'BOQ-GEN',
            'type': 'service',
            'list_price': 0.0,
        })

    def _open_record(self, record):
        return {
            'type': 'ir.actions.act_window',
            'res_model': record._name,
            'res_id': record.id,
            'view_mode': 'form',
            'target': 'current',
        }

    # ------------------------------------------------------------------ #
    # Utilities
    # ------------------------------------------------------------------ #
    def action_view_raw_response(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _("AI Raw Response"),
                'message': (self.ai_raw_response or _("(no response stored)"))[:500],
                'sticky': True,
                'type': 'info',
            },
        }
