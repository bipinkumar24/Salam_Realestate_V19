# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from datetime import date, timedelta


class WarrantyClaim(models.Model):
    """
    Post-handover warranty claim during Defect Liability Period (DLP).

    Key distinction:
      warranty — defect present at handover, contractor's obligation to fix at zero cost
      maintenance — normal wear and tear, owner's responsibility

    Status: open → assessed → contractor_notified → rectified → closed
    """
    _name = 'salaam.warranty.claim'
    _description = 'Warranty Claim'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'report_date desc'

    # ── IDENTITY ──────────────────────────────────────────────────────────────
    name = fields.Char(
        string='Claim Reference', readonly=True, copy=False, default='New',
    )
    state = fields.Selection([
        ('open',                 'Open'),
        ('assessed',             'Assessed — Warranty Confirmed'),
        ('maintenance_only',     'Assessed — Maintenance (Not Warranty)'),
        ('contractor_notified',  'Contractor Notified'),
        ('rectified',            'Rectified — Awaiting Verification'),
        ('closed',               'Closed'),
        ('rejected',             'Rejected — Not Under Warranty'),
    ], string='Status', default='open', tracking=True)

    # ── LINKS ─────────────────────────────────────────────────────────────────
    certificate_id = fields.Many2one(
        'salaam.handover.certificate',
        string='Handover Certificate', required=True, ondelete='cascade',
        index=True,
    )
    property_id = fields.Many2one(
        related='certificate_id.property_id', store=True,
    )
    project_id = fields.Many2one(
        related='certificate_id.project_id', store=True,
    )
    buyer_id = fields.Many2one(
        related='certificate_id.buyer_id', store=True,
    )
    contractor_id = fields.Many2one('res.partner', string='Responsible Contractor')

    # ── DEFECT ────────────────────────────────────────────────────────────────
    title = fields.Char(string='Claim Title', required=True)
    description = fields.Text(string='Defect Description')
    room = fields.Selection([
        ('entrance', 'Entrance / Lobby'), ('living', 'Living Room'),
        ('dining', 'Dining Room'), ('kitchen', 'Kitchen'),
        ('master_bed', 'Master Bedroom'), ('bed_2', 'Bedroom 2'),
        ('bathroom', 'Bathroom'), ('balcony', 'Balcony'),
        ('other', 'Other'),
    ], string='Location')
    category = fields.Selection([
        ('structural', 'Structural'), ('mep', 'MEP'),
        ('finishes', 'Finishes'), ('joinery', 'Joinery'),
        ('waterproofing', 'Waterproofing'), ('other', 'Other'),
    ], string='Category')
    severity = fields.Selection([
        ('critical', 'Critical'), ('major', 'Major'),
        ('minor', 'Minor'), ('cosmetic', 'Cosmetic'),
    ], string='Severity', default='minor')

    # ── CLASSIFICATION ────────────────────────────────────────────────────────
    claim_type = fields.Selection([
        ('warranty',     'Warranty — Contractor Obligation'),
        ('maintenance',  'Maintenance — Owner Responsibility'),
        ('undetermined', 'Under Assessment'),
    ], string='Claim Type', default='undetermined', tracking=True)

    # ── DLP CHECK ─────────────────────────────────────────────────────────────
    report_date = fields.Date(
        string='Date Reported', default=fields.Date.today, required=True,
    )
    within_dlp = fields.Boolean(
        string='Within DLP', compute='_compute_within_dlp', store=True,
    )
    dlp_end_date = fields.Date(
        related='certificate_id.dlp_end_date', store=True,
    )
    rectification_deadline = fields.Date(string='Contractor Rectification Deadline')
    rectified_date = fields.Date(string='Date Rectified')
    closed_date = fields.Date(string='Date Closed')
    assessed_by = fields.Many2one('res.users', string='Assessed By')

    @api.depends('report_date', 'dlp_end_date')
    def _compute_within_dlp(self):
        for rec in self:
            if rec.report_date and rec.dlp_end_date:
                rec.within_dlp = rec.report_date <= rec.dlp_end_date
            else:
                rec.within_dlp = False

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'salaam.warranty.claim'
                ) or _('New')
        return super().create(vals_list)

    def action_assess_warranty(self):
        for rec in self:
            rec.state = 'assessed'
            rec.claim_type = 'warranty'
            rec.assessed_by = self.env.user
            rec.rectification_deadline = date.today() + timedelta(days=21)

    def action_assess_maintenance(self):
        for rec in self:
            rec.state = 'maintenance_only'
            rec.claim_type = 'maintenance'
            rec.assessed_by = self.env.user

    def action_notify_contractor(self):
        self.state = 'contractor_notified'

    def action_rectified(self):
        self.write({'state': 'rectified', 'rectified_date': date.today()})

    def action_close(self):
        self.write({'state': 'closed', 'closed_date': date.today()})

    def action_reject(self):
        self.state = 'rejected'
