# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError
from datetime import date


class UnitPhaseLink(models.Model):
    """
    Unit-to-Construction-Phase link.

    Bridges property.details (unit) with salaam.construction.phase (build stage).

    TWO link types per unit:

    1. progress_reference
       The phase whose progress % is displayed to the customer on the portal
       and to sales staff on the property form.
       VISIBILITY ONLY — no gate, no automation.
       Example: "MEP Works" phase — shows customer their floor is 67% done.

    2. practical_completion
       The phase whose completion (100%) marks this unit as physically ready.
       THIS IS THE ONLY HARD GATE in the system.
       When this phase hits 100%:
         → property.construction_status = 'practically_complete'
         → property.practical_completion_date set
         → Snag inspection can begin (salaam.snag.list can be created)
         → Handover certificate can be issued

    Why separate?
       For a tower block, the customer-facing progress phase might be
       "Interior Fit-Out" (shows exciting visible work). But practical
       completion might require both "Fit-Out" AND "Commissioning" to be
       100%. The link allows this nuance.

    For Salaam City (1,600 units / 4 phases):
       Units in Tower A link to Tower A's phases.
       Units in Tower B link to Tower B's phases.
       Infrastructure phases link to all units in the development.
    """
    _name = 'salaam.unit.phase.link'
    _description = 'Unit — Construction Phase Link'
    _order = 'property_id, link_type'

    property_id = fields.Many2one(
        'property.details',
        string='Unit / Property',
        required=True, ondelete='cascade', index=True,
    )
    project_id = fields.Many2one(
        'salaam.construction.project',
        string='Construction Project',
        required=True, index=True,
    )
    phase_id = fields.Many2one(
        'salaam.construction.phase',
        string='Construction Phase',
        required=True,
    )
    link_type = fields.Selection([
        ('progress_reference',  'Progress Reference (visibility only)'),
        ('practical_completion','Practical Completion Gate (hard gate)'),
    ], string='Link Type', required=True, default='progress_reference')

    # ── LIVE DATA from linked phase ───────────────────────────────────────────
    # Computed with getattr fallbacks — salaam.construction.phase field names
    # may vary across installations (progress/completion_pct, planned_end/date_end, etc.)
    phase_progress = fields.Float(
        compute='_compute_phase_data', store=True,
        string='Phase Progress (%)',
    )
    phase_state = fields.Char(
        compute='_compute_phase_data', store=True,
        string='Phase Status',
    )
    phase_planned_end = fields.Date(
        compute='_compute_phase_data', store=True,
        string='Phase Planned End',
    )
    phase_name = fields.Char(
        compute='_compute_phase_data', store=True,
    )

    @api.depends('phase_id')
    def _compute_phase_data(self):
        for rec in self:
            phase = rec.phase_id
            if phase:
                # progress: try common field names
                rec.phase_progress = (
                    getattr(phase, 'progress', 0) or
                    getattr(phase, 'completion_pct', 0) or
                    getattr(phase, 'percent_complete', 0) or 0.0
                )
                # state: try common field names
                rec.phase_state = (
                    getattr(phase, 'state', False) or
                    getattr(phase, 'status', False) or False
                )
                # planned_end: try common field names
                rec.phase_planned_end = (
                    getattr(phase, 'planned_end', False) or
                    getattr(phase, 'date_end', False) or
                    getattr(phase, 'end_date', False) or
                    getattr(phase, 'date_planned_end', False) or False
                )
                # name: standard field, safe
                rec.phase_name = getattr(phase, 'name', False) or False
            else:
                rec.phase_progress = 0.0
                rec.phase_state = False
                rec.phase_planned_end = False
                rec.phase_name = False

    notes = fields.Char(string='Notes')

    @api.constrains('property_id', 'link_type')
    def _check_unique_practical_completion(self):
        """Only one practical_completion link allowed per unit."""
        for rec in self:
            if rec.link_type == 'practical_completion':
                existing = self.search([
                    ('property_id', '=', rec.property_id.id),
                    ('link_type', '=', 'practical_completion'),
                    ('id', '!=', rec.id),
                ])
                if existing:
                    raise UserError(_(
                        'Unit %s already has a Practical Completion phase linked: %s. '
                        'Only one practical completion gate is allowed per unit.'
                    ) % (rec.property_id.name, existing[0].phase_id.name))

    @api.model
    def create(self, vals):
        return super().create(vals)


class ConstructionPhaseUnitTrigger(models.Model):
    """
    Extends salaam.construction.phase.
    When a phase reaches 100% / completed state:
      → finds all units linked via practical_completion
      → updates their construction_status
      → sets practical_completion_date
    """
    _inherit = 'salaam.construction.phase'

    linked_unit_count = fields.Integer(
        compute='_compute_linked_units',
        string='Linked Units',
    )
    practical_completion_unit_count = fields.Integer(
        compute='_compute_linked_units',
        string='Units Gated on This Phase',
    )

    @api.depends()
    def _compute_linked_units(self):
        Link = self.env['salaam.unit.phase.link']
        for rec in self:
            rec.linked_unit_count = Link.search_count([
                ('phase_id', '=', rec.id)
            ])
            rec.practical_completion_unit_count = Link.search_count([
                ('phase_id', '=', rec.id),
                ('link_type', '=', 'practical_completion'),
            ])

    def action_complete(self):
        """Override to trigger unit construction status update."""
        super().action_complete()
        # Find all units gated on this phase for practical completion
        links = self.env['salaam.unit.phase.link'].search([
            ('phase_id', 'in', self.ids),
            ('link_type', '=', 'practical_completion'),
        ])
        for link in links:
            prop = link.property_id
            if prop.stage in ('contracted', 'under_construction'):
                prop.write({
                    'stage': 'practically_complete',
                    'practical_completion_date': date.today(),
                    'construction_status': 'practically_complete',
                })
                prop.message_post(body=_(
                    'Practical completion reached. Construction phase "%s" completed. '
                    'Snagging can now begin.'
                ) % link.phase_id.name)
