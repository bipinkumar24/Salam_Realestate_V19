# -*- coding: utf-8 -*-
{
    'name': 'Salaam Off-Plan Construction Link',
    'version': '19.0.1.0.0',
    'summary': 'Unit-level construction progress visibility and handover readiness gate',
    'description': """
salaam_offplan_link
===================
Bridges the COMMERCIAL TRACK (sales/reservations) with the
CONSTRUCTION TRACK (phases/progress) at the unit level.

Design principle:
-----------------
Construction progress does NOT gate reservations or bookings.
The only hard gate is at HANDOVER — a certificate cannot be issued
until practical completion is confirmed on the unit.

Everything else is VISIBILITY only — sales staff and portal
customers can see live construction progress on their unit.

Models:
-------
1. salaam.unit.phase.link
   Links a property.details unit to a specific buruuj.phase.
   Two link types:
     - practical_completion: the phase whose completion marks the unit
       as physically ready for snagging (hard gate)
     - progress_reference: the phase whose progress % is shown to the
       customer (visibility only — no gate)

   When the practical_completion phase reaches 100%:
     -> property.construction_status = 'practically_complete'
     -> property.practical_completion_date set
     -> Snag list can now be created for this unit
     -> Handover certificate can now be issued

2. Extends property.details with:
   - construction_phase_id: linked progress phase
   - construction_progress: live % from linked phase (computed)
   - construction_status: not_started / under_construction /
     practically_complete / handed_over
   - practical_completion_date
   - handover_ready: computed Boolean — True only when
     practical_completion phase = 100% AND snag list closed
   - expected_completion_date: from linked phase.planned_end
   - construction_project_id: parent project

Portal display:
---------------
Property detail page shows a construction progress bar for
reserved/contracted units. Available units show expected
completion date. No progress shown for unreserved units
(commercial sensitivity).
""",
    'author': 'Salaam Investment Bank — IAFAO',
    'category': 'Real Estate',
    'license': 'LGPL-3',
    'depends': [
        'base', 'mail',
        'rental_management',
        'buruuj_project',
        'salaam_handover',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/sequences.xml',
        'views/property_base_fallback.xml',
        'views/unit_phase_link_views.xml',
        'views/property_construction_views.xml',
        'views/construction_phase_inherit_views.xml',
        'views/menus.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'post_init_hook': 'post_init_hook',
}