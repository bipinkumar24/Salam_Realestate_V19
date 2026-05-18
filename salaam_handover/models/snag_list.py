# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError
from datetime import date, timedelta


class SnagList(models.Model):
    """
    Master snagging record per unit per inspection round.

    Workflow:
      draft → in_progress → contractor_response → re_inspection → closed

    One snag list per unit per round. Multiple rounds allowed
    (initial inspection, re-inspection after rectification, etc.).
    A handover certificate can only be issued when all snag items
    on the latest round are verified closed.

    For Salaam City — 1,600 units across 4 phases.
    """
    _name = 'salaam.snag.list'
    _description = 'Snagging List'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'property_id, inspection_date desc'

    # ── IDENTITY ──────────────────────────────────────────────────────────────
    name = fields.Char(
        string='Snag Reference', readonly=True,
        copy=False, default='New',
    )
    round_number = fields.Integer(
        string='Inspection Round', default=1,
        help='1 = Initial inspection, 2 = Re-inspection after rectification, etc.',
    )
    state = fields.Selection([
        ('draft',               'Draft'),
        ('in_progress',         'Inspection In Progress'),
        ('contractor_response', 'Awaiting Contractor Response'),
        ('re_inspection',       'Re-Inspection Required'),
        ('closed',              'Closed — All Items Verified'),
    ], string='Status', default='draft', tracking=True)

    # ── LINKS ─────────────────────────────────────────────────────────────────
    project_id = fields.Many2one(
        'project.project',
        string='Construction Project', required=True, index=True,
    )
    property_id = fields.Many2one(
        'property.details',
        string='Unit / Property', required=True, index=True, tracking=True
    )
    phase_id = fields.Many2one(
        'buruuj.phase',
        string='Construction Phase',
    )
    sale_contract_id = fields.Many2one(
        'dev.contract.sale',
        string='Sale Contract (SCT)',
    )

    # ── PARTIES ───────────────────────────────────────────────────────────────
    inspector_id = fields.Many2one(
        'res.users', string='Lead Inspector',
        default=lambda self: self.env.user,
    )
    contractor_id = fields.Many2one(
        'res.partner', string='Main Contractor',
    )
    buyer_id = fields.Many2one(
        'res.partner', string='Buyer / Customer',
    )
    buyer_attended = fields.Boolean(
        string='Buyer Attended Inspection', default=False,
    )

    # ── DATES ─────────────────────────────────────────────────────────────────
    inspection_date = fields.Date(
        string='Inspection Date', required=True,
        default=fields.Date.today,
    )
    contractor_response_deadline = fields.Date(
        string='Contractor Response Deadline',
        compute='_compute_deadline', store=True,
    )
    re_inspection_date = fields.Date(string='Re-Inspection Date')
    closed_date = fields.Date(string='Date Closed')

    # ── SNAG ITEMS ────────────────────────────────────────────────────────────
    snag_item_ids = fields.One2many(
        'salaam.snag.item', 'snag_list_id', string='Snag Items',
    )
    total_items = fields.Integer(
        compute='_compute_counts', store=True, string='Total Items',
    )
    open_items = fields.Integer(
        compute='_compute_counts', store=True, string='Open Items',
    )
    verified_items = fields.Integer(
        compute='_compute_counts', store=True, string='Verified Closed',
    )
    critical_items = fields.Integer(
        compute='_compute_counts', store=True, string='Critical Items',
    )
    completion_pct = fields.Float(
        compute='_compute_counts', store=True,
        string='Completion (%)', digits=(5, 1),
    )

    # ── NOTES ─────────────────────────────────────────────────────────────────
    general_notes = fields.Text(string='General Inspection Notes')
    contractor_comments = fields.Text(string='Contractor Response / Comments')

    # ── SEQUENCE ──────────────────────────────────────────────────────────────
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code(
                   'salaam.snag.list'
                ) or _('New')
        return super().create(vals_list)

    # ── COMPUTES ──────────────────────────────────────────────────────────────
    @api.depends('inspection_date')
    def _compute_deadline(self):
        for rec in self:
            if rec.inspection_date:
                rec.contractor_response_deadline = rec.inspection_date + timedelta(days=14)
            else:
                rec.contractor_response_deadline = False

    @api.depends(
        'snag_item_ids', 'snag_item_ids.state', 'snag_item_ids.severity',
    )
    def _compute_counts(self):
        for rec in self:
            items = rec.snag_item_ids
            total = len(items)
            verified = len(items.filtered(lambda i: i.state == 'verified'))
            open_count = len(items.filtered(lambda i: i.state in ('open', 'contractor_notified', 'rejected')))
            critical = len(items.filtered(lambda i: i.severity == 'critical' and i.state != 'verified'))
            rec.total_items = total
            rec.open_items = open_count
            rec.verified_items = verified
            rec.critical_items = critical
            rec.completion_pct = (verified / total * 100) if total else 0.0

    # ── WORKFLOW ──────────────────────────────────────────────────────────────
    def action_start_inspection(self):
        self.state = 'in_progress'

    def action_issue_to_contractor(self):
        for rec in self:
            if not rec.snag_item_ids:
                raise UserError(_('Add at least one snag item before issuing to contractor.'))
            # Notify all snag items
            rec.snag_item_ids.filtered(
                lambda i: i.state == 'open'
            ).write({'state': 'contractor_notified'})
            rec.state = 'contractor_response'
            rec.message_post(body=_(
                'Snag list issued to contractor %s. %d items. Deadline: %s'
            ) % (rec.contractor_id.name or '—', len(rec.snag_item_ids),
                 rec.contractor_response_deadline))

    def action_schedule_reinspection(self):
        self.state = 're_inspection'

    def action_close(self):
        for rec in self:
            if rec.open_items > 0:
                raise UserError(_(
                    'Cannot close: %d snag item(s) still open. '
                    'All items must be verified before closing.'
                ) % rec.open_items)
            rec.state = 'closed'
            rec.closed_date = date.today()
            rec.message_post(body=_('Snag list closed. All %d items verified.') % rec.total_items)


class SnagItem(models.Model):
    """
    Individual defect item on a snag list.
    Room-by-room classification, trade responsibility, severity.
    """
    _name = 'salaam.snag.item'
    _description = 'Snag Item'
    _inherit = ['mail.thread']
    _order = 'snag_list_id, room, sequence'

    snag_list_id = fields.Many2one(
        'salaam.snag.list', required=True, ondelete='cascade', index=True,
    )
    sequence = fields.Integer(default=10)
    project_id = fields.Many2one(
        related='snag_list_id.project_id', store=True,
    )
    property_id = fields.Many2one(
        related='snag_list_id.property_id', store=True,
    )

    # ── LOCATION ──────────────────────────────────────────────────────────────
    room = fields.Selection([
        ('entrance',      'Entrance / Lobby'),
        ('living',        'Living Room'),
        ('dining',        'Dining Room'),
        ('kitchen',       'Kitchen'),
        ('master_bed',    'Master Bedroom'),
        ('bed_2',         'Bedroom 2'),
        ('bed_3',         'Bedroom 3'),
        ('bed_4',         'Bedroom 4'),
        ('master_bath',   'Master Bathroom'),
        ('bathroom_2',    'Bathroom 2'),
        ('bathroom_3',    'Bathroom 3'),
        ('balcony',       'Balcony / Terrace'),
        ('store',         'Store Room / Utility'),
        ('corridor',      'Internal Corridor'),
        ('common_lobby',  'Common Area — Lobby'),
        ('common_corridor','Common Area — Corridor'),
        ('car_park',      'Car Park'),
        ('external',      'External / Facade'),
        ('roof',          'Roof / Roof Terrace'),
        ('plant_room',    'Plant Room / Services'),
        ('other',         'Other'),
    ], string='Room / Location', required=True)

    # ── DEFECT ────────────────────────────────────────────────────────────────
    description = fields.Text(string='Defect Description', required=True)
    category = fields.Selection([
        ('structural',   'Structural'),
        ('mep',          'MEP (Mechanical / Electrical / Plumbing)'),
        ('finishes',     'Finishes (Paint, Tiling, Flooring)'),
        ('joinery',      'Joinery (Doors, Windows, Built-ins)'),
        ('waterproofing','Waterproofing'),
        ('external',     'External Works / Landscape'),
        ('common_area',  'Common Area'),
        ('other',        'Other'),
    ], string='Defect Category', required=True)

    severity = fields.Selection([
        ('critical',  'Critical — Unsafe / Unfit for occupation'),
        ('major',     'Major — Significant impact on use'),
        ('minor',     'Minor — Aesthetic / functional'),
        ('cosmetic',  'Cosmetic — No functional impact'),
    ], string='Severity', required=True, default='minor', tracking=True)

    # ── RESPONSIBILITY ────────────────────────────────────────────────────────
    responsible_trade = fields.Selection([
        ('main_contractor', 'Main Contractor'),
        ('civil',           'Civil / Structural Sub'),
        ('mep',             'MEP Sub-Contractor'),
        ('fit_out',         'Fit-Out / Finishes Sub'),
        ('facade',          'Facade Contractor'),
        ('landscape',       'Landscape Contractor'),
        ('developer',       'Developer — Design Issue'),
        ('tbd',             'To Be Determined'),
    ], string='Responsible Trade', default='main_contractor')

    rectification_deadline = fields.Date(string='Rectification Deadline')

    # ── STATUS ────────────────────────────────────────────────────────────────
    state = fields.Selection([
        ('open',                 'Open'),
        ('contractor_notified',  'Contractor Notified'),
        ('rectified',            'Rectified — Awaiting Verification'),
        ('verified',             'Verified Closed'),
        ('rejected',             'Rectification Rejected — Redo'),
    ], string='Status', default='open', tracking=True)

    rectified_date = fields.Date(string='Date Rectified by Contractor')
    verified_date = fields.Date(string='Date Verified by Inspector')
    verified_by = fields.Many2one('res.users', string='Verified By')
    rejection_reason = fields.Text(string='Rejection Reason')

    # ── WORKFLOW ──────────────────────────────────────────────────────────────
    def action_mark_rectified(self):
        self.write({
            'state': 'rectified',
            'rectified_date': date.today(),
        })

    def action_verify(self):
        self.write({
            'state': 'verified',
            'verified_date': date.today(),
            'verified_by': self.env.uid,
        })

    def action_reject(self):
        for rec in self:
            rec.state = 'rejected'
            rec.message_post(body=_(
                'Rectification rejected. Reason: %s'
            ) % (rec.rejection_reason or 'See comments'))
