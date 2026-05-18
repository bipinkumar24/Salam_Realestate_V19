# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class PropertyConstructionInherit(models.Model):
    """
    Extends property.details with construction visibility fields.

    DESIGN PRINCIPLE:
      - Reservations & bookings: NO dependency on construction (commercial track)
      - Construction progress: VISIBILITY ONLY for reserved/contracted units
      - Handover certificate: HARD GATE — requires practical_completion_date set

    What the customer sees on the portal:
      Available unit:  "Expected Completion: Q3 2027"
      Reserved unit:   Progress bar + phase name + expected completion date
      Contracted unit: Progress bar + phase name + expected completion date
      Practically complete: "Your unit is ready for snagging inspection"
      Handover ready:  "Your unit is ready for handover"
    """
    _inherit = 'property.details'

    # ── CONSTRUCTION PROJECT LINK ──────────────────────────────────────────────
    construction_project_id = fields.Many2one(
        'project.project',
        string='Construction Project',
        index=True,
        help='The construction project building this unit',
    )

    # ── PHASE LINKS ───────────────────────────────────────────────────────────
    unit_phase_link_ids = fields.One2many(
        'salaam.unit.phase.link',
        'property_id',
        string='Construction Phase Links',
    )

    # ── PROGRESS VISIBILITY (computed from progress_reference link) ────────────
    construction_progress = fields.Float(
        string='Construction Progress (%)',
        compute='_compute_construction_progress',
        store=True,
        digits=(5, 1),
        help='Live progress from the linked progress reference phase. Visibility only.',
    )
    construction_phase_name = fields.Char(
        string='Current Construction Phase',
        compute='_compute_construction_progress',
        store=True,
    )
    expected_completion_date = fields.Date(
        string='Expected Completion Date',
        compute='_compute_construction_progress',
        store=True,
        help='Planned end date of the practical completion phase',
    )

    # ── CONSTRUCTION STATUS ───────────────────────────────────────────────────
    construction_status = fields.Selection([
        ('not_started',          'Not Started'),
        ('under_construction',   'Under Construction'),
        ('practically_complete', 'Practically Complete'),
        ('handed_over',          'Handed Over'),
    ], string='Construction Status', default='not_started', tracking=True)

    practical_completion_date = fields.Date(
        string='Practical Completion Date',
        readonly=True,
        help='Set automatically when the practical completion phase reaches 100%',
    )

    # ── HANDOVER READINESS (the only hard gate) ────────────────────────────────
    handover_ready = fields.Boolean(
        string='Handover Ready',
        compute='_compute_handover_ready',
        store=True,
        help='True only when: practical completion confirmed AND snag list closed',
    )
    snag_list_closed = fields.Boolean(
        string='Snag List Closed',
        compute='_compute_handover_ready',
        store=True,
    )

    # ── COMPUTES ──────────────────────────────────────────────────────────────
    @api.depends(
        'unit_phase_link_ids',
        'unit_phase_link_ids.link_type',
        'unit_phase_link_ids.phase_progress',
        'unit_phase_link_ids.phase_name',
        'unit_phase_link_ids.phase_planned_end',
        'unit_phase_link_ids.phase_state',
    )
    def _compute_construction_progress(self):
        for rec in self:
            links = rec.unit_phase_link_ids
            # Progress from 'progress_reference' link
            prog_link = links.filtered(
                lambda l: l.link_type == 'progress_reference'
            )
            if prog_link:
                pl = prog_link[0]
                rec.construction_progress = pl.phase_progress
                rec.construction_phase_name = pl.phase_name
            else:
                # Fall back to practical completion phase progress
                pc_link = links.filtered(
                    lambda l: l.link_type == 'practical_completion'
                )
                if pc_link:
                    rec.construction_progress = pc_link[0].phase_progress
                    rec.construction_phase_name = pc_link[0].phase_name
                else:
                    rec.construction_progress = 0.0
                    rec.construction_phase_name = False

            # Expected completion from practical_completion link
            pc_link = links.filtered(
                lambda l: l.link_type == 'practical_completion'
            )
            rec.expected_completion_date = (
                pc_link[0].phase_planned_end if pc_link else False
            )

    @api.depends(
        'practical_completion_date',
        'snag_list_ids',
        'snag_list_ids.state',
    )
    def _compute_handover_ready(self):
        for rec in self:
            # Snag list closed?
            closed_snag = rec.snag_list_ids.filtered(
                lambda s: s.state == 'closed'
            )
            rec.snag_list_closed = bool(closed_snag)
            # Handover ready = practical completion confirmed + snag closed
            rec.handover_ready = bool(
                rec.practical_completion_date and rec.snag_list_closed
            )
            # Auto-advance stage if ready
            if rec.handover_ready and rec.stage == 'practically_complete':
                rec.stage = 'handover_ready'
                rec.construction_status = 'practically_complete'

    # ── VALIDATION: handover certificate gate ─────────────────────────────────
    def check_handover_readiness(self):
        """
        Called by salaam.handover.certificate before issuing.
        Raises UserError if unit is not physically ready.
        """
        self.ensure_one()
        if not self.practical_completion_date:
            raise UserError(_(
                'Cannot issue handover certificate for %s: '
                'Practical completion has not been confirmed. '
                'The construction phase must reach 100%% first.'
            ) % self.name)
        if not self.snag_list_closed:
            raise UserError(_(
                'Cannot issue handover certificate for %s: '
                'No closed snag list found. '
                'Complete the snagging inspection and close all items first.'
            ) % self.name)

    # ── SMART BUTTONS ─────────────────────────────────────────────────────────
    def action_open_phase_links(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Construction Links — %s') % self.name,
            'res_model': 'salaam.unit.phase.link',
            'view_mode': 'list,form',
            'domain': [('property_id', '=', self.id)],
            'context': {
                'default_property_id': self.id,
                'default_project_id': self.construction_project_id.id,
            },
        }

    # ── PROGRESS DISPLAY FOR PORTAL ───────────────────────────────────────────
    def get_portal_progress_data(self):
        """
        Returns dict of construction data for portal QWeb template.
        Called from portal controller.
        Only shows data to customers who have an active reservation or contract.
        """
        self.ensure_one()
        return {
            'show_progress': self.stage in (
                'reserved_offplan', 'contracted',
                'under_construction', 'practically_complete',
                'handover_ready',
            ),
            'progress': self.construction_progress,
            'phase_name': self.construction_phase_name,
            'expected_date': self.expected_completion_date,
            'construction_status': self.construction_status,
            'handover_ready': self.handover_ready,
            'practical_completion_date': self.practical_completion_date,
        }
