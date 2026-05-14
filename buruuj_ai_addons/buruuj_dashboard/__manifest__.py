# -*- coding: utf-8 -*-
{
    'name': 'Buruuj Construction - Executive Dashboard',
    'version': '19.0.1.0.0',
    'category': 'Construction',
    'summary': 'CEO portfolio dashboard with cross-module KPIs',
    'description': """
Executive Dashboard
====================
Aggregated portfolio view for the CEO and senior leadership:
* Project health (Green/Amber/Red)
* Cash position & receivables aging
* Top risks across all projects
* Subcontractor exposure and payments due
* Tender pipeline value and win rate
* Manpower and equipment utilization
""",
    'author': 'Buruuj Construction Co.',
    'license': 'OPL-1',
    'depends': [
        'buruuj_base', 'buruuj_project', 'buruuj_tendering',
        'buruuj_subcontractor', 'buruuj_ipc',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/buruuj_dashboard_views.xml',
    ],
    'installable': True,
    'application': False,
}
