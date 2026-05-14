# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError
from datetime import date, timedelta


class HandoverCertificate(models.Model):
    """
    Formal unit handover certificate.
    Generated only when all snag items on the linked snag list are verified closed.
    Triggers property.stage → sold (final) and starts DLP clock.

    Status: draft → issued → buyer_signed → registered
    """
    _name = 'salaam.handover.certificate'
    _description = 'Handover Certificate'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'handover_date desc'

    # ── IDENTITY ──────────────────────────────────────────────────────────────
    name = fields.Char(
        string='Certificate Reference', readonly=True,
        copy=False, default='New',
    )
    state = fields.Selection([
        ('draft',        'Draft'),
        ('issued',       'Issued to Buyer'),
        ('buyer_signed', 'Buyer Signed'),
        ('registered',   'Registered'),
    ], string='Status', default='draft', tracking=True)

    # ── LINKS ─────────────────────────────────────────────────────────────────
    project_id = fields.Many2one(
        'salaam.construction.project', string='Project', required=True,
    )
    property_id = fields.Many2one(
        'property.details', string='Unit / Property',
        required=True, index=True, tracking=True,
    )
    snag_list_id = fields.Many2one(
        'salaam.snag.list', string='Final Snag List',
        help='Must be a closed snag list — all items verified',
    )
    sale_contract_id = fields.Many2one(
        'dev.contract.sale', string='Sale Contract (SCT)',
    )
    buyer_id = fields.Many2one(
        'res.partner', string='Buyer', required=True,
    )

    # ── PARTIES ───────────────────────────────────────────────────────────────
    issued_by = fields.Many2one(
        'res.users', string='Issued By', default=lambda self: self.env.user,
    )
    witness_id = fields.Many2one('res.partner', string='Witness')

    # ── DATES ─────────────────────────────────────────────────────────────────
    handover_date = fields.Date(
        string='Handover Date', required=True, default=fields.Date.today,
        tracking=True,
    )
    buyer_signed_date = fields.Date(string='Buyer Signature Date')
    registered_date = fields.Date(string='Registration Date')
    dlp_start_date = fields.Date(
        string='DLP Start Date',
        compute='_compute_dlp', store=True,
    )
    dlp_end_date = fields.Date(
        string='DLP End Date (12 months)',
        compute='_compute_dlp', store=True,
    )
    dlp_expired = fields.Boolean(
        string='DLP Expired', compute='_compute_dlp', store=True,
    )

    # ── KEYS & DOCUMENTS ──────────────────────────────────────────────────────
    keys_released = fields.Boolean(string='Keys Released to Buyer', default=False)
    keys_release_date = fields.Date(string='Keys Release Date')
    meter_readings = fields.Text(
        string='Meter Readings at Handover',
        help='Electricity, water, gas meter readings recorded at handover',
    )
    outstanding_payments_cleared = fields.Boolean(
        string='Outstanding Payments Confirmed Cleared', default=False,
    )
    snagging_notes = fields.Text(string='Outstanding Matters / Agreed Actions')

    # ── WARRANTY CLAIMS ───────────────────────────────────────────────────────
    warranty_claim_ids = fields.One2many(
        'salaam.warranty.claim', 'certificate_id', string='Warranty Claims',
    )
    warranty_claim_count = fields.Integer(compute='_compute_warranty_count')
    open_warranty_count = fields.Integer(compute='_compute_warranty_count')

    # ── COMPUTES ──────────────────────────────────────────────────────────────
    @api.depends('handover_date', 'state')
    def _compute_dlp(self):
        today = date.today()
        for rec in self:
            if rec.handover_date and rec.state in ('buyer_signed', 'registered'):
                rec.dlp_start_date = rec.handover_date
                rec.dlp_end_date = rec.handover_date.replace(
                    year=rec.handover_date.year + 1
                )
                rec.dlp_expired = today > rec.dlp_end_date
            else:
                rec.dlp_start_date = False
                rec.dlp_end_date = False
                rec.dlp_expired = False

    @api.depends('warranty_claim_ids', 'warranty_claim_ids.state')
    def _compute_warranty_count(self):
        for rec in self:
            rec.warranty_claim_count = len(rec.warranty_claim_ids)
            rec.open_warranty_count = len(
                rec.warranty_claim_ids.filtered(
                    lambda w: w.state not in ('closed', 'rejected')
                )
            )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code(
                   'salaam.handover.certificate'
                ) or _('New')
        return super().create(vals_list)

    # ── WORKFLOW ──────────────────────────────────────────────────────────────
    def action_issue(self):
        for rec in self:
            if not rec.snag_list_id:
                raise UserError(_('Link a closed snag list before issuing the certificate.'))
            if rec.snag_list_id.state != 'closed':
                raise UserError(_(
                    'Snag list %s is not closed. All snag items must be verified '
                    'before a handover certificate can be issued.'
                ) % rec.snag_list_id.name)
            if not rec.outstanding_payments_cleared:
                raise UserError(_(
                    'Confirm outstanding payments are cleared before issuing the certificate.'
                ))
            rec.state = 'issued'
            rec.message_post(body=_(
                'Handover certificate issued to buyer %s for unit %s.'
            ) % (rec.buyer_id.name, rec.property_id.name))

    def action_buyer_signed(self):
        for rec in self:
            rec.state = 'buyer_signed'
            rec.buyer_signed_date = date.today()
            # Release keys if not already done
            if not rec.keys_released:
                rec.keys_released = True
                rec.keys_release_date = date.today()
            rec.message_post(body=_(
                'Buyer %s signed handover certificate on %s. DLP starts: %s. DLP ends: %s.'
            ) % (rec.buyer_id.name, rec.buyer_signed_date,
                 rec.dlp_start_date, rec.dlp_end_date))

    def action_register(self):
        self.write({'state': 'registered', 'registered_date': date.today()})


