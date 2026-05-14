# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError
from datetime import date


class CrmLeadReservation(models.Model):
    """
    Extends crm.lead with:
    1. Priority Number — auto-generated reference: PRI/DDMMYYYY/NNNN
    2. File Number    — auto-generated reference: FILE/DDMMYYYY/NNNN
    3. Auto-create Reservation when lead is saved (on first save with partner + property)
    4. Manual "Create Reservation" button
    """
    _inherit = 'crm.lead'

    # ── SALAAM CUSTOM FIELDS ──────────────────────────────────────────────────
    priority_number = fields.Char(
        string='Priority Number',
        readonly=True, copy=False, default='',
        help='Auto-generated: PRI/DDMMYYYY/NNNN',
    )
    file_number = fields.Char(
        string='File Number',
        readonly=True, copy=False, default='',
        help='Auto-generated: FILE/DDMMYYYY/NNNN',
    )
    property_id = fields.Many2one(
        'property.details',
        string='Unit / Property of Interest',
        help='The unit the customer is interested in reserving',
    )
    reservation_id = fields.Many2one(
        'salaam.reservation',
        string='Linked Reservation',
        readonly=True,
        help='Auto-created when Priority/File numbers are generated',
    )
    reservation_state = fields.Selection(
        related='reservation_id.state',
        string='Reservation Status',
        readonly=True,
        store=False,
    )

    # ── NUMBER GENERATION ────────────────────────────────────────────────────
    def _generate_numbers(self):
        """
        Generate Priority Number and File Number.
        Format: PREFIX/DDMMYYYY/NNNN
        Example: PRI/06042026/0001 and FILE/06042026/0001
        Uses ir.sequence for the sequential counter (monthly reset).
        """
        today = date.today()
        date_part = today.strftime('%d%m%Y')  # DDMMYYYY

        for rec in self:
            if rec.priority_number and rec.file_number:
                raise UserError(_('Priority and File numbers already generated for this lead.'))

            # Get sequential number
            seq_pri = self.env['ir.sequence'].next_by_code('salaam.crm.priority') or '0001'
            seq_file = self.env['ir.sequence'].next_by_code('salaam.crm.file') or '0001'

            rec.write({
                'priority_number': f'PRI/{date_part}/{seq_pri}',
                'file_number': f'FILE/{date_part}/{seq_file}',
            })
            rec.message_post(body=_(
                'Priority Number: <b>%s</b> | File Number: <b>%s</b>'
            ) % (rec.priority_number, rec.file_number))

    # ── AUTO-CREATE RESERVATION ───────────────────────────────────────────────
    def _auto_create_reservation(self):
        """
        Create a draft Reservation linked to this CRM lead.
        Called after generating priority/file numbers.
        Requires: partner_id and property_id to be set on the lead.
        """
        for rec in self:
            if rec.reservation_id:
                continue  # Already has a reservation

            if not rec.partner_id:
                rec.message_post(body=_(
                    'Reservation not auto-created: no Customer set on this lead. '
                    'Set the Customer and use Create Reservation button.'
                ))
                continue

            if not rec.property_id:
                rec.message_post(body=_(
                    'Reservation not auto-created: no Unit / Property of Interest set. '
                    'Set the property and use Create Reservation button.'
                ))
                continue

            # Check unit is still available
            prop = rec.property_id
            if prop.stage not in ('available', 'draft'):
                rec.message_post(body=_(
                    'Reservation not auto-created: unit %s is currently %s (not available).'
                ) % (prop.name, prop.stage))
                continue

            # Determine agent: lead salesperson if set
            agent_id = rec.user_id.id if rec.user_id else False

            reservation = self.env['salaam.reservation'].create({
                'partner_id': rec.partner_id.id,
                'property_id': rec.property_id.id,
                'agent_id': agent_id,
                'crm_lead_id': rec.id,
                'reservation_date': date.today(),
            })

            rec.reservation_id = reservation.id
            rec.message_post(body=_(
                'Reservation <a href="#" data-oe-model="salaam.reservation" '
                'data-oe-id="%d">%s</a> created automatically.'
            ) % (reservation.id, reservation.name))

    # ── MAIN ACTION BUTTON ────────────────────────────────────────────────────
    def action_generate_and_reserve(self):
        """
        Main button: Generate Priority/File numbers AND create Reservation.
        Called from the CRM lead form button.
        """
        self.ensure_one()
        self._generate_numbers()
        self._auto_create_reservation()
        return True

    # ── AUTO-TRIGGER ON SAVE ──────────────────────────────────────────────────
    def write(self, vals):
        result = super().write(vals)
        # Auto-generate numbers when lead is saved with both partner and property set
        # Use sudo() to avoid cache issues with fields from other modules
        # Only trigger if partner_id or property_id changed (or both are already set)
        trigger_fields = {'partner_id', 'property_id'}
        if not trigger_fields.intersection(vals.keys()):
            return result
        for rec in self:
            try:
                # Read only the fields we need via direct SQL-safe approach
                rec_data = rec.read(['partner_id', 'property_id',
                                     'priority_number', 'file_number'])[0]
                if (rec_data.get('partner_id') and rec_data.get('property_id')
                        and not rec_data.get('priority_number')
                        and not rec_data.get('file_number')):
                    rec._generate_numbers()
                    rec._auto_create_reservation()
            except Exception:
                pass  # Never block save
        return result

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)

        for rec, vals in zip(records, vals_list):
            if vals.get('partner_id') and vals.get('property_id'):
                try:
                    rec._generate_numbers()
                    rec._auto_create_reservation()
                except Exception:
                    pass

        return records

    # ── OPEN RESERVATION ─────────────────────────────────────────────────────
    def action_open_reservation(self):
        """Open the linked reservation record."""
        self.ensure_one()
        if not self.reservation_id:
            raise UserError(_('No reservation linked to this lead yet.'))
        return {
            'type': 'ir.actions.act_window',
            'name': _('Reservation — %s') % self.reservation_id.name,
            'res_model': 'salaam.reservation',
            'res_id': self.reservation_id.id,
            'view_mode': 'form',
        }

    # ── MANUAL CREATE RESERVATION (if auto failed) ────────────────────────────
    def action_create_reservation_manual(self):
        """Manually create reservation (if auto-creation failed or wasn't triggered)."""
        self.ensure_one()
        if self.reservation_id:
            return self.action_open_reservation()
        if not self.priority_number:
            self._generate_numbers()
        self._auto_create_reservation()
        if self.reservation_id:
            return self.action_open_reservation()
