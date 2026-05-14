# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError


class DevContractBase(models.AbstractModel):
    """Abstract mixin providing common fields and logic for all Salaam
    Developer & Contractor contract types."""
    _name = 'dev.contract.base'
    _description = 'Developer Contract Base Mixin'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'name desc'

    # ── IDENTITY ──────────────────────────────────────────────────────────────
    name = fields.Char(
        string='Reference', required=True, copy=False, readonly=True,
        index=True, default=lambda self: _('New'),
        tracking=True,
    )
    contract_type = fields.Selection(
        selection=[
            ('sale', 'Sale Contract'),
            ('istisna', 'Istisna (Construction Finance)'),
            ('ijara', 'Ijara (Lease)'),
            ('musharaka', 'Diminishing Musharaka (JV)'),
            ('subcontractor', 'Subcontractor Agreement'),
            ('consultancy', 'Consultancy Agreement'),
        ],
        string='Contract Type', required=True, tracking=True,
    )
    state = fields.Selection(
        selection=[
            ('draft', 'Draft'),
            ('submitted', 'Submitted'),
            ('under_review', 'Under Review'),
            ('approved', 'Approved'),
            ('signed', 'Signed'),
            ('active', 'Active'),
            ('completed', 'Completed'),
            ('cancelled', 'Cancelled'),
        ],
        string='Status', default='draft', required=True,
        tracking=True, copy=False,
    )
    company_id = fields.Many2one(
        'res.company', string='Branch', required=True,
        default=lambda self: self.env.company,
        tracking=True,
    )

    # ── PROPERTY & BRE LINKS ──────────────────────────────────────────────────
    property_id = fields.Many2one(
        'property.details', string='Property',
        tracking=True, ondelete='restrict',
    )
    bre_application_id = fields.Many2one(
        'bre.customer.application', string='BRE Application',
        tracking=True, ondelete='restrict',
    )

    # ── FINANCIAL ─────────────────────────────────────────────────────────────
    currency_id = fields.Many2one(
        'res.currency', string='Currency', required=True,
        default=lambda self: self.env.ref('base.USD'),
    )
    contract_value = fields.Monetary(
        string='Contract Value', currency_field='currency_id',
        required=True, tracking=True,
    )

    # ── DATES ─────────────────────────────────────────────────────────────────
    date_start = fields.Date(string='Start Date', required=True, tracking=True)
    date_end = fields.Date(string='End Date', required=True, tracking=True)

    # ── SHARIA ────────────────────────────────────────────────────────────────
    sharia_required = fields.Boolean(
        string='Sharia Compliance Required',
        default=False, tracking=True,
    )
    sharia_certified = fields.Boolean(
        string='Sharia Certified', default=False,
        readonly=True, copy=False, tracking=True,
    )
    sharia_ref = fields.Char(
        string='Sharia Board Reference',
        help='Reference number issued by the Sharia Supervisory Board e.g. SSB-2026-042',
    )
    sharia_certified_by = fields.Many2one(
        'res.users', string='Certified By (Sharia Officer)',
        readonly=True, copy=False,
    )
    sharia_certified_date = fields.Date(
        string='Sharia Certification Date',
        readonly=True, copy=False,
    )

    # ── RESPONSIBILITY ────────────────────────────────────────────────────────
    officer_id = fields.Many2one(
        'res.users', string='Contract Officer', required=True,
        default=lambda self: self.env.user,
        tracking=True,
    )
    approved_by = fields.Many2one(
        'res.users', string='Approved By',
        readonly=True, copy=False, tracking=True,
    )
    approved_date = fields.Date(
        string='Approval Date', readonly=True, copy=False,
    )

    # ── MILESTONES & CLAUSES ──────────────────────────────────────────────────
    milestone_ids = fields.One2many(
        'dev.contract.milestone', 'contract_id',
        string='Milestones',
    )
    milestone_count = fields.Integer(
        string='Milestones', compute='_compute_milestone_count',
    )
    clause_ids = fields.Many2many(
        'dev.contract.clause', string='Contract Clauses',
    )

    # ── NOTES ─────────────────────────────────────────────────────────────────
    note = fields.Html(string='Internal Notes')

    # ── COMPUTED ──────────────────────────────────────────────────────────────
    @api.depends('milestone_ids')
    def _compute_milestone_count(self):
        for rec in self:
            rec.milestone_count = len(rec.milestone_ids)

    # ── SEQUENCE GENERATION ───────────────────────────────────────────────────
    def _get_sequence_code(self):
        """Override per model to return the sequence code."""
        return 'dev.contract.default'

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    self._get_sequence_code()
                ) or _('New')
        return super().create(vals_list)

    # ── CONSTRAINTS ───────────────────────────────────────────────────────────
    @api.constrains('date_start', 'date_end')
    def _check_dates(self):
        for rec in self:
            if rec.date_start and rec.date_end and rec.date_end < rec.date_start:
                raise ValidationError(_('End Date cannot be before Start Date.'))

    # ── WORKFLOW ACTIONS ──────────────────────────────────────────────────────
    def action_submit(self):
        self._check_required_fields()
        self.write({'state': 'submitted'})

    def action_under_review(self):
        self.write({'state': 'under_review'})

    def action_approve(self):
        if self.sharia_required and not self.sharia_certified:
            raise UserError(_(
                'This contract requires Sharia Supervisory Board certification '
                'before it can be approved. Please obtain SSB sign-off first.'
            ))
        self.write({
            'state': 'approved',
            'approved_by': self.env.user.id,
            'approved_date': fields.Date.today(),
        })

    def action_sign(self):
        if self.state != 'approved':
            raise UserError(_('Contract must be in Approved state before signing.'))
        self.write({'state': 'signed'})

    def action_activate(self):
        self.write({'state': 'active'})

    def action_complete(self):
        self.write({'state': 'completed'})

    def action_cancel(self):
        self.write({'state': 'cancelled'})

    def action_reset_draft(self):
        self.write({'state': 'draft', 'approved_by': False, 'approved_date': False})

    def action_certify_sharia(self):
        """Called by Sharia Officer to certify compliance."""
        self.ensure_one()
        if not self.env.user.has_group('salaam_dev_contracts.group_dev_contracts_sharia'):
            raise UserError(_('Only a Sharia Officer can certify this contract.'))
        self.write({
            'sharia_certified': True,
            'sharia_certified_by': self.env.user.id,
            'sharia_certified_date': fields.Date.today(),
        })
        self.message_post(
            body=_('Contract certified as Sharia-compliant by %s on %s. Reference: %s') % (
                self.env.user.name,
                fields.Date.today(),
                self.sharia_ref or 'Pending SSB ref',
            )
        )

    def action_open_milestones(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Milestones — %s') % self.name,
            'res_model': 'dev.contract.milestone',
            'view_mode': 'list,form',
            'domain': [('res_model', '=', self._name), ('res_id', '=', self.id)],
            'context': {
                'default_res_model': self._name,
                'default_res_id': self.id,
            },
        }

    def _check_required_fields(self):
        """Hook for subclasses to add pre-submit validation."""
        pass
