# -*- coding: utf-8 -*-
{
    'name': 'Buruuj Construction - Subcontractor Management',
    'version': '19.0.1.0.0',
    'category': 'Construction',
    'summary': 'Subcontractor lifecycle: prequalification, contracts, work orders, scorecard',
    'description': """
Subcontractor Management
=========================
* Prequalification with documents and expiry alerts
* Subcontract agreement with retention, advance, milestone payments
* Work Orders against active subcontracts
* Performance scorecard (quality, schedule, safety, payments)
* Back-charge management
* Liquidated Damages tracking
* Retention release tied to DLP
""",
    'author': 'Buruuj Construction Co.',
    'license': 'OPL-1',
    'depends': ['buruuj_base', 'buruuj_project', 'mail'],
    'data': [
        'security/ir.model.access.csv',
        'views/buruuj_subcontract_views.xml',
        'views/buruuj_workorder_views.xml',
        'views/buruuj_scorecard_views.xml',
        'views/buruuj_backcharge_views.xml',
        'views/buruuj_subcontractor_menus.xml',
    ],
    'installable': True,
    'application': False,
}
