# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError
from datetime import date, timedelta


class SalaamReservation(models.Model):
    """
    Off-Plan Reservation Agreement.

    Sits between unit selection and full BRE financing application.
    Entirely on the COMMERCIAL TRACK — no dependency on construction progress.

    A customer can reserve a unit:
      - On launch day (before construction starts)
      - During construction at any stage
      - At practical completion

    The reservation is a lightweight commitment:
      1. Customer pays reservation deposit (typically 2–5% of unit price)
      2. Cooling-off period starts (14 days — customer can withdraw, deposit returned)
      3. Reservation expiry countdown starts (typically 60 days)
      4. Within expiry: customer converts to full BRE application + sale contract
      5. After conversion: reservation → BRE application auto-created

    Status flow:
      draft → active → converted (success)
                    → expired   (no conversion within deadline)
                    → cancelled (customer or developer initiated)

    On expiry/cancellation:
      - Unit returns to Available
      - Deposit handling per refund_policy field
    """
    _name = 'salaam.reservation'
    _description = 'Off-Plan Reservation Agreement'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'reservation_date desc'

    # ── IDENTITY ──────────────────────────────────────────────────────────────
    name = fields.Char(
        string='Reservation Reference',
        readonly=True, copy=False, default='New',
    )
    state = fields.Selection([
        ('draft',           'Draft'),
        ('active',          'Active — In Cooling-Off'),
        ('new_application', 'New Application'),
        ('confirmed',       'Confirmed — Awaiting Contract'),
        ('converted',       'Converted to Contract'),
        ('expired',         'Expired'),
        ('cancelled',       'Cancelled'),
    ], string='Status', default='draft', tracking=True)

    # ── UNIT ──────────────────────────────────────────────────────────────────
    property_id = fields.Many2one(
        'property.details',
        string='Unit / Property',
        required=True, index=True, tracking=True,
        domain="[('stage','in',['available','draft'])]",
    )
    unit_price = fields.Monetary(
        string='Unit Listed Price',
        compute='_compute_property_fields',
        currency_field='currency_id',
        readonly=True,
        store=True,
    )
    project_id = fields.Many2one(
        'salaam.project',
        string='Development / Project',
        related='property_id.salaam_project_id',
        store=True,
        readonly=False,
    )
    sub_project_id = fields.Many2one(
        'salaam.sub.project',
        string='Sub Project',
        related='property_id.salaam_sub_project_id',
        store=True,
        readonly=False,
        domain="[('project_id', '=', project_id)]",
    )

    # ── CUSTOMER ──────────────────────────────────────────────────────────────
    partner_id = fields.Many2one(
        'res.partner', string='Customer', required=True, tracking=True,
    )
    nationality = fields.Many2one('res.country', string='Customer Nationality')
    id_type = fields.Selection([
        ('national_id', 'National ID'),
        ('passport',    'Passport'),
        ('residence',   'Residence Permit'),
    ], string='ID Type')
    id_number = fields.Char(string='ID Number')

    # ── AGENT ─────────────────────────────────────────────────────────────────
    agent_id = fields.Many2one('res.users', string='Sales Agent')
    team_id = fields.Many2one(
        'crm.team', string='Sales Team',
        help='Sales team for commission calculation',
    )
    crm_lead_id = fields.Integer(
        string='CRM Lead ID',
        help='ID of the linked CRM Lead/Opportunity (crm module)',
    )
    # ── DATES & PERIODS ───────────────────────────────────────────────────────
    reservation_date = fields.Date(
        string='Reservation Date',
        required=True, default=fields.Date.today, tracking=True,
    )
    # Cooling-off: customer can withdraw with full deposit refund
    cooling_off_days = fields.Integer(
        string='Cooling-Off Period (days)', default=14,
        help='Customer can cancel with full refund within this period',
    )
    cooling_off_end = fields.Date(
        string='Cooling-Off End Date',
        compute='_compute_dates', store=True,
    )
    in_cooling_off = fields.Boolean(
        string='In Cooling-Off Period',
        compute='_compute_dates', store=True,
    )
    # Conversion deadline: must convert to contract by this date
    conversion_days = fields.Integer(
        string='Conversion Period (days)', default=60,
        help='Customer must sign sale contract and confirm financing within this period',
    )
    conversion_deadline = fields.Date(
        string='Conversion Deadline',
        compute='_compute_dates', store=True,
    )
    days_to_deadline = fields.Integer(
        string='Days to Conversion Deadline',
        compute='_compute_dates', store=True,
    )
    deadline_status = fields.Selection([
        ('ok',     'On Track'),
        ('amber',  'Amber — < 14 days'),
        ('red',    'Red — < 7 days'),
        ('expired','Expired'),
    ], compute='_compute_dates', store=True)

    # Outcome dates
    converted_date = fields.Date(string='Conversion Date', readonly=True)
    expiry_date = fields.Date(string='Date Expired / Cancelled', readonly=True)

    # ── DEPOSIT ───────────────────────────────────────────────────────────────
    currency_id = fields.Many2one(
        'res.currency',
        default=lambda self: self.env.company.currency_id,
    )
    deposit_pct = fields.Float(
        string='Deposit (%)', default=2.0,
        help='Reservation deposit as % of unit price',
    )
    deposit_amount = fields.Monetary(
        string='Deposit Amount',
        compute='_compute_deposit', store=True,
        currency_field='currency_id',
    )
    deposit_received = fields.Monetary(
        string='Deposit Received',
        compute='_compute_deposit', store=True,
        currency_field='currency_id',
    )
    deposit_outstanding = fields.Monetary(
        string='Deposit Outstanding',
        compute='_compute_deposit', store=True,
        currency_field='currency_id',
    )
    deposit_fully_paid = fields.Boolean(
        string='Deposit Fully Paid',
        compute='_compute_deposit', store=True,
    )

    # ── REFUND POLICY ─────────────────────────────────────────────────────────
    refund_policy = fields.Selection([
        ('full',    'Full Refund'),
        ('partial', 'Partial Refund (50%)'),
        ('forfeit', 'Deposit Forfeited'),
        ('na',      'N/A — Converted'),
    ], string='Cancellation Refund Policy', default='full')
    cancellation_reason = fields.Selection([
        ('customer_cooling_off',  'Customer — Within Cooling-Off Period'),
        ('customer_financing',    'Customer — Financing Not Secured'),
        ('customer_change_mind',  'Customer — Change of Mind'),
        ('developer_cancelled',   'Developer — Unit Cancelled'),
        ('expired_no_contact',    'Expired — No Customer Response'),
        ('other',                 'Other'),
    ], string='Cancellation / Expiry Reason')

    # ── CONVERTED TO ─────────────────────────────────────────────────────────
    bre_application_id = fields.Integer(
        string='BRE Application ID',
        readonly=True,
        help='ID of the linked BRE Financing Application (bank_realestate_collab module)',
    )
    sale_contract_id = fields.Many2one(
        'dev.contract.sale',
        string='Sale Contract (SCT)',
        readonly=True,
    )

    # ── PAYMENT LINES ─────────────────────────────────────────────────────────
    # ── ACCOUNT PAYMENTS (real accounting entries) ───────────────────────────
    payment_ids = fields.One2many(
        'account.payment', 'reservation_id',
        string='Deposit Payments',
        domain=[('is_reservation_deposit', '=', True)],
    )
    payment_count = fields.Integer(compute='_compute_payment_count')
    # Legacy custom payment lines (kept for backward compatibility)
    legacy_payment_ids = fields.One2many(
        'salaam.reservation.payment', 'reservation_id',
        string='Legacy Deposit Records',
    )

    # ── NOTES ─────────────────────────────────────────────────────────────────
    special_conditions = fields.Text(string='Special Conditions / Notes')
    internal_notes = fields.Text(string='Internal Notes')

    @api.depends('property_id')
    def _compute_property_fields(self):
        for rec in self:
            prop = rec.property_id
            if prop:
                price = (getattr(prop, 'price', 0) or
                         getattr(prop, 'sale_price', 0) or
                         getattr(prop, 'list_price', 0) or
                         getattr(prop, 'selling_price', 0) or 0)
                rec.unit_price = price
            else:
                rec.unit_price = 0

    # ── SEQUENCE ──────────────────────────────────────────────────────────────
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'salaam.reservation'
                ) or _('New')
        return super().create(vals_list)

    # ── COMPUTES ──────────────────────────────────────────────────────────────
    @api.depends('reservation_date', 'cooling_off_days', 'conversion_days', 'state')
    def _compute_dates(self):
        today = date.today()
        for rec in self:
            if rec.reservation_date:
                cooling_end = rec.reservation_date + timedelta(days=rec.cooling_off_days)
                conv_deadline = rec.reservation_date + timedelta(days=rec.conversion_days)
                rec.cooling_off_end = cooling_end
                rec.in_cooling_off = today <= cooling_end and rec.state in ('active', 'confirmed')
                rec.conversion_deadline = conv_deadline
                days_left = (conv_deadline - today).days
                rec.days_to_deadline = days_left
                if rec.state in ('converted', 'cancelled'):
                    rec.deadline_status = 'ok'
                elif days_left < 0:
                    rec.deadline_status = 'expired'
                elif days_left < 7:
                    rec.deadline_status = 'red'
                elif days_left < 14:
                    rec.deadline_status = 'amber'
                else:
                    rec.deadline_status = 'ok'
            else:
                rec.cooling_off_end = False
                rec.in_cooling_off = False
                rec.conversion_deadline = False
                rec.days_to_deadline = 0
                rec.deadline_status = 'ok'

    @api.depends('unit_price', 'deposit_pct',
                 'payment_ids.amount', 'payment_ids.state',
                 'legacy_payment_ids.amount', 'legacy_payment_ids.state')
    def _compute_deposit(self):
        for rec in self:
            required = (rec.unit_price or 0) * (rec.deposit_pct / 100)
            # account.payment: posted/sent/reconciled = money received
            received = sum(
                p.amount for p in rec.payment_ids
                if p.state in ('posted', 'sent', 'reconciled')
            )
            # legacy custom payment records
            received += sum(
                p.amount for p in rec.legacy_payment_ids
                if p.state in ('received', 'reconciled')
            )
            rec.deposit_amount = required
            rec.deposit_received = received
            rec.deposit_outstanding = max(0, required - received)
            rec.deposit_fully_paid = received >= required and required > 0

    @api.depends('payment_ids', 'legacy_payment_ids')
    def _compute_payment_count(self):
        for rec in self:
            rec.payment_count = len(rec.payment_ids) + len(rec.legacy_payment_ids)

    @api.depends('name', 'partner_id', 'property_id')
    def _compute_display_name(self):
        for rec in self:
            parts = [rec.name]
            if rec.partner_id:
                parts.append(rec.partner_id.name)
            if rec.property_id:
                parts.append(rec.property_id.name)
            rec.display_name = ' — '.join(parts)

    # ── WORKFLOW ──────────────────────────────────────────────────────────────

    def action_register_payment(self):
        """Open account.payment form pre-filled for this reservation deposit."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Register Deposit Payment'),
            'res_model': 'account.payment',
            'view_mode': 'form',
            'context': {
                'default_reservation_id': self.id,
                'default_is_reservation_deposit': True,
                'default_partner_id': self.partner_id.id,
                'default_amount': self.deposit_outstanding or self.deposit_amount,
                'default_currency_id': self.currency_id.id,
                'default_payment_type': 'inbound',
                'default_partner_type': 'customer',
                'default_ref': self.name,
            },
        }

    def action_open_payments(self):
        """Open all account.payment records for this reservation."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Payments — %s') % self.name,
            'res_model': 'account.payment',
            'view_mode': 'list,form',
            'domain': [('reservation_id', '=', self.id)],
            'context': {
                'default_reservation_id': self.id,
                'default_is_reservation_deposit': True,
                'default_partner_id': self.partner_id.id,
                'default_payment_type': 'inbound',
                'default_partner_type': 'customer',
            },
        }


    def action_create_application(self):
        """Open the BRE application wizard to collect required fields."""
        self.ensure_one()

        # If already created — open it directly
        if self.bre_application_id:
            try:
                rec = self.env['bre.customer.application'].browse(
                    self.bre_application_id)
                if rec.exists():
                    return {
                        'type': 'ir.actions.act_window',
                        'name': _('BRE Customer Application'),
                        'res_model': 'bre.customer.application',
                        'res_id': rec.id,
                        'view_mode': 'form',
                        'target': 'current',
                    }
            except Exception:
                pass

        # Open wizard
        return {
            'type': 'ir.actions.act_window',
            'name': _('Create BRE Application'),
            'res_model': 'salaam.create.bre.application.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_reservation_id': self.id,
            },
        }


    def action_activate(self):
        """
        Activate reservation:
        - Validates unit is still Available
        - Sets unit stage to reserved_offplan
        - Starts cooling-off and conversion countdown
        """
        for rec in self:
            if rec.property_id.stage not in ('available', 'draft'):
                raise UserError(_(
                    'Unit %s is no longer available. Current stage: %s'
                ) % (rec.property_id.name, rec.property_id.stage))
            rec.state = 'active'
            rec.property_id.stage = 'reserved_offplan'
            rec.message_post(body=_(
                'Reservation activated for %s on %s. '
                'Cooling-off ends: %s. Conversion deadline: %s.'
            ) % (rec.property_id.name, rec.reservation_date,
                 rec.cooling_off_end, rec.conversion_deadline))

    def action_confirm(self):
        """
        Confirm reservation — cooling-off period passed, deposit received.
        Unit stays reserved. Conversion countdown continues.
        """
        for rec in self:
            if not rec.deposit_fully_paid:
                raise UserError(_(
                    'Deposit not fully paid. Received: %s / Required: %s %s'
                ) % (rec.deposit_received, rec.deposit_amount,
                     rec.currency_id.symbol))
            rec.state = 'confirmed'
            rec.message_post(body=_(
                'Reservation confirmed. Deposit fully received: %s %s. '
                'Conversion deadline: %s.'
            ) % (rec.deposit_amount, rec.currency_id.symbol, rec.conversion_deadline))

    def action_convert(self):
        """
        Convert reservation to full BRE application and sale contract.
        - Attempts to create BRE application if bank_realestate_collab is installed
        - Sets property stage → contracted
        - Links BRE application ID to reservation
        """
        for rec in self:
            if rec.state not in ('active', 'confirmed'):
                raise UserError(_('Only Active or Confirmed reservations can be converted.'))

            bre_id = False
            bre_name = 'N/A'

            # Only create BRE application if the model exists in the registry
            if 'bre.application' in self.env:
                try:
                    bre = self.env['bre.application'].create({
                        'partner_id': rec.partner_id.id,
                        'property_id': rec.property_id.id,
                        'agent_id': rec.agent_id.id if rec.agent_id else False,
                        'crm_lead_id': rec.crm_lead_id or False,
                        'financing_type': 'murabaha',
                        'state': 'draft',
                    })
                    bre_id = bre.id
                    bre_name = bre.name
                except Exception as e:
                    # Log but do not block conversion if BRE creation fails
                    rec.message_post(body=_(
                        'Note: BRE application could not be created automatically: %s. '
                        'Please create it manually.'
                    ) % str(e))

            rec.bre_application_id = bre_id
            rec.state = 'converted'
            rec.converted_date = date.today()
            rec.property_id.stage = 'contracted'
            rec.message_post(body=_(
                'Reservation converted. BRE Application: %s. '
                'Unit %s → Contracted.'
            ) % (bre_name, rec.property_id.name))

    def action_cancel(self):
        """
        Cancel reservation — returns unit to Available.
        Deposit handling per refund_policy.
        """
        for rec in self:
            rec.state = 'cancelled'
            rec.expiry_date = date.today()
            # Return unit to available
            if rec.property_id.stage in ('reserved_offplan', 'contracted'):
                rec.property_id.stage = 'available'
            refund_msg = {
                'full':    'Full deposit refund due.',
                'partial': 'Partial refund (50%) due.',
                'forfeit': 'Deposit forfeited per contract terms.',
                'na':      '',
            }.get(rec.refund_policy, '')
            rec.message_post(body=_(
                'Reservation cancelled. Reason: %s. %s Unit returned to Available.'
            ) % (rec.cancellation_reason or '—', refund_msg))

    def action_mark_expired(self):
        """Mark reservation as expired — used by scheduled action or manual trigger."""
        for rec in self:
            if rec.state not in ('active', 'confirmed'):
                continue
            rec.state = 'expired'
            rec.expiry_date = date.today()
            if rec.property_id.stage in ('reserved_offplan',):
                rec.property_id.stage = 'available'
            rec.message_post(body=_(
                'Reservation expired on %s. Unit %s returned to Available.'
            ) % (rec.conversion_deadline, rec.property_id.name))

    def action_open_bre_application(self):
        """Open the linked BRE application record."""
        self.ensure_one()
        if not self.bre_application_id:
            return
        if 'bre.application' not in self.env:
            raise UserError(_(
                'The BRE application module (bank_realestate_collab) is not installed. '
                'BRE Application ID: %d'
            ) % self.bre_application_id)
        return {
            'type': 'ir.actions.act_window',
            'name': _('BRE Application'),
            'res_model': 'bre.application',
            'res_id': self.bre_application_id,
            'view_mode': 'form',
        }

    # ── SCHEDULED ACTION (cron) ───────────────────────────────────────────────
    @api.model
    def cron_expire_reservations(self):
        """Called daily — auto-expires reservations past conversion deadline."""
        today = date.today()
        expired = self.search([
            ('state', 'in', ('active', 'confirmed')),
            ('conversion_deadline', '<', today),
        ])
        expired.action_mark_expired()
