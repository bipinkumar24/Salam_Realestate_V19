# -*- coding: utf-8 -*-
{
    'name': 'Salaam Pre-Development',
    'version': '19.0.1.0.0',
    'category': 'Real Estate',
    'summary': 'Pre-Development pipeline: Market Research → Land → Feasibility → Concept → Unit Mix → Design',
    'description': '''
Salaam City Pre-Development Pipeline
=====================================
Tracks a real estate development from initial market research through
to design approval and handover to construction and sales teams.

Stages
------
1. Market Research  - Demand analysis, comparables, target demographic
2. Land Acquisition - Site identification, due diligence, acquisition
3. Feasibility Study - Financial and planning feasibility assessment
4. Concept Design   - Architectural concept, massing, design brief
5. Unit Mix         - Define unit types, quantities, areas, prices
6. Design           - Detailed design, consultant appointments
7. Approved         - Handed over to construction and sales

Integration
-----------
- Links to salaam.project (Development / Project master)
- Creates property.details units from the Unit Mix
- Creates salaam.tender records for design consultancy
- Links to salaam.construction.project for build phase
    ''',
    'author': 'Salaam Investment Bank — IAFAO',
    'depends': [
        'base',
        'mail',
        'rental_management',
        'salaam_reservation',
        'salaam_procurement',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/sequences.xml',
        'views/predevelopment_views.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
