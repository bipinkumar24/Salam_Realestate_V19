# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from datetime import date


class ReservationPayment(models.Model):
    """
    Deposit payment record linked to a reservation.
    Supports staged payments (e.g. 2% on reservation, 8% on contract signing).

    Status: pending → received → reconciled / refunded
    """
    _name = 'salaam.reservation.payment'
    _description = 'Reservation Deposit Payment'
    _order = 'reservation_id, payment_date'

    reservation_id = fields.Many2one(
        'salaam.reservation',
        string='Reservation', required=True,
        ondelete='cascade', index=True,
    )
    property_id = fields.Many2one(
        related='reservation_id.property_id', store=True,
    )
    partner_id = fields.Many2one(
        related='reservation_id.partner_id', store=True,
    )
    currency_id = fields.Many2one(
        related='reservation_id.currency_id', store=True,
    )

    # ── PAYMENT DETAILS ───────────────────────────────────────────────────────
    name = fields.Char(string='Payment Reference', required=True)
    payment_date = fields.Date(
        string='Payment Date', default=fields.Date.today,
    )
    amount = fields.Monetary(
        string='Amount', currency_field='currency_id', required=True,
    )
    payment_method = fields.Selection([
        ('bank_transfer', 'Bank Transfer'),
        ('cheque',        'Cheque'),
        ('cash',          'Cash'),
        ('card',          'Credit / Debit Card'),
        ('crypto',        'Crypto / Digital Asset'),
    ], string='Payment Method', default='bank_transfer')

    receipt_reference = fields.Char(string='Receipt / Transaction Reference')
    bank_name = fields.Char(string='Bank Name')
    notes = fields.Char(string='Notes')

    # ── STATUS ────────────────────────────────────────────────────────────────
    state = fields.Selection([
        ('pending',     'Pending'),
        ('received',    'Received — Unreconciled'),
        ('reconciled',  'Reconciled'),
        ('refunded',    'Refunded'),
    ], string='Status', default='pending')

    received_by = fields.Many2one('res.users', string='Received By')
    reconciled_date = fields.Date(string='Reconciliation Date')
    refunded_date = fields.Date(string='Refund Date')
    refund_reference = fields.Char(string='Refund Reference')

    # ── WORKFLOW ──────────────────────────────────────────────────────────────
    def action_mark_received(self):
        self.write({
            'state': 'received',
            'received_by': self.env.uid,
        })

    def action_reconcile(self):
        self.write({
            'state': 'reconciled',
            'reconciled_date': date.today(),
        })

    def action_refund(self):
        self.write({
            'state': 'refunded',
            'refunded_date': date.today(),
        })


class PropertyOffPlanStageInherit(models.Model):
    """
    Extends property.details with off-plan stages and reservation links.

    Additional stages added to the existing Selection field:
      reserved_offplan — customer has signed reservation, deposit paid
      contracted       — BRE approved, sale contract signed
      under_construction — building phase active
      practically_complete — construction done, snagging started
      handover_ready   — snag list closed, certificate can be issued
      handed_over      — buyer signed handover certificate, DLP running

    Note: 'available', 'reserved', 'booked', 'sold' already exist.
    We extend the selection and add reservation tracking fields.
    """
    _inherit = 'property.details'

    # ── EXTEND STAGE SELECTION ────────────────────────────────────────────────
    # Override the stage field to add off-plan stages
    # In Odoo 19, we add new selection values via _sql_constraints
    # and the field override pattern.
    stage = fields.Selection(
        selection_add=[
            ('reserved_offplan',     'Reserved (Off-Plan)'),
            ('contracted',           'Contracted'),
            ('under_construction',   'Under Construction'),
            ('practically_complete', 'Practically Complete'),
            ('handover_ready',       'Handover Ready'),
            ('handed_over',          'Handed Over'),
        ],
        ondelete={
            'reserved_offplan':     'cascade',
            'contracted':           'cascade',
            'under_construction':   'cascade',
            'practically_complete': 'cascade',
            'handover_ready':       'cascade',
            'handed_over':          'cascade',
        },
        tracking=True,
    )

    # ── RESERVATION LINKS ─────────────────────────────────────────────────────
    reservation_ids = fields.One2many(
        'salaam.reservation', 'property_id', string='Reservations',
    )
    active_reservation_id = fields.Many2one(
        'salaam.reservation',
        string='Active Reservation',
        compute='_compute_active_reservation',
        store=True,
    )
    reservation_count = fields.Integer(
        compute='_compute_active_reservation', store=True,
    )
    active_reservation_name = fields.Char(
        related='active_reservation_id.name', store=True,
    )
    active_reservation_partner = fields.Many2one(
        related='active_reservation_id.partner_id', store=True,
    )
    active_reservation_deadline = fields.Date(
        related='active_reservation_id.conversion_deadline', store=True,
    )
    active_reservation_deadline_status = fields.Selection(
        related='active_reservation_id.deadline_status', store=True,
    )
    deposit_fully_paid = fields.Boolean(
        related='active_reservation_id.deposit_fully_paid', store=True,
    )

    @api.depends('reservation_ids', 'reservation_ids.state')
    def _compute_active_reservation(self):
        for rec in self:
            active = rec.reservation_ids.filtered(
                lambda r: r.state in ('active', 'confirmed')
            ).sorted('reservation_date', reverse=True)
            rec.active_reservation_id = active[0] if active else False
            rec.reservation_count = len(rec.reservation_ids)

    def action_open_reservations(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Reservations — %s') % self.name,
            'res_model': 'salaam.reservation',
            'view_mode': 'list,form',
            'domain': [('property_id', '=', self.id)],
            'context': {'default_property_id': self.id},
        }

    def action_create_reservation(self):
        """Quick action to create a new reservation for this unit."""
        self.ensure_one()
        if self.stage not in ('available', 'draft'):
            raise UserError(_(
                'Cannot create reservation: unit is %s. '
                'Only Available units can be reserved.'
            ) % self.stage)
        return {
            'type': 'ir.actions.act_window',
            'name': _('New Reservation — %s') % self.name,
            'res_model': 'salaam.reservation',
            'view_mode': 'form',
            'context': {
                'default_property_id': self.id,
                'default_unit_price': self.price,
            },
        }
