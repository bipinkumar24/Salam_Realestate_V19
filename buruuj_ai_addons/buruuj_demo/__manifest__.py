# -*- coding: utf-8 -*-
{
    'name': 'Buruuj Construction - Demo Data',
    'version': '19.0.1.0.0',
    'category': 'Construction',
    'summary': 'Realistic demo data: projects, subcontractors, IPCs, DPRs, equipment',
    'description': """
Demo Data for Buruuj Construction
==================================
Bootstraps a realistic Buruuj environment with:
* 3 active projects (high-rise tower, road upgrade, government fitout)
* 1 won tender (linked to a project) + 1 in-submission tender
* 3 clients, 2 consultants, 6 subcontractors with trade specializations
* 3 active subcontracts with work orders
* Sample client and subcontractor IPCs
* Daily Progress Reports, RFIs, NCRs, snags
* Equipment register with allocations
* HSE: toolbox talks, permits, incidents
* Drawings, transmittals, submittals
* Variation orders, milestones, risks
* Master rates database

Install AFTER all the buruuj_* modules. Safe to uninstall — drops only its records.
""",
    'author': 'Buruuj Construction Co.',
    'license': 'OPL-1',
    'depends': [
        'buruuj_base', 'buruuj_tendering', 'buruuj_project',
        'buruuj_subcontractor', 'buruuj_ipc', 'buruuj_site_ops',
        'buruuj_plant', 'buruuj_hse', 'buruuj_quality', 'buruuj_contract',
        'buruuj_dashboard', 'buruuj_tools', 'buruuj_rental',
    ],
    'data': [
        'data/01_partners.xml',
        'data/02_rates.xml',
        'data/03_tenders.xml',
        'data/04_projects.xml',
        'data/05_subcontracts.xml',
        'data/06_workorders.xml',
        'data/07_ipcs.xml',
        'data/08_site_ops.xml',
        'data/09_plant.xml',
        'data/10_hse.xml',
        'data/11_quality.xml',
        'data/12_contracts.xml',
        'data/13_tools.xml',
        'data/14_rentals.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
