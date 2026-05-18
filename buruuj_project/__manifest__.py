# -*- coding: utf-8 -*-
{
    'name': 'Buruuj Construction - Project Management',
    'version': '19.0.1.0.0',
    'category': 'Construction',
    'summary': 'Construction project extensions: WBS, baseline, milestones, variations',
    'description': """
Project Management for Construction
====================================
Extends Odoo Project with construction-specific fields and adds:
* Project hierarchy: Project → Phase → WBS → Task
* Frozen baseline budget vs actual cost tracking
* Variation Order (Change Order) workflow
* Milestone-based billing schedule
* Project risk register
* Project health indicators (Green / Amber / Red)
* Gantt views on Phases and WBS
* S-curve progress snapshots (planned vs earned %)
""",
    'author': 'Buruuj Construction Co.',
    'license': 'OPL-1',
    'depends': ['buruuj_base', 'buruuj_tendering', 'project', 'mail'],
    'data': [
        'security/ir.model.access.csv',
        'views/project_project_views.xml',
        'views/buruuj_phase_views.xml',
        'views/buruuj_wbs_views.xml',
        'views/buruuj_variation_views.xml',
        'views/buruuj_milestone_views.xml',
        'views/buruuj_risk_views.xml',
        'views/buruuj_progress_views.xml',
        'views/buruuj_project_menus.xml',
    ],
    'installable': True,
    'application': False,
}
