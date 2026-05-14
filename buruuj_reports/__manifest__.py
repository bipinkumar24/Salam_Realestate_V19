# -*- coding: utf-8 -*-
{
    'name': 'Buruuj Construction - PDF Reports',
    'version': '19.0.1.0.0',
    'category': 'Construction',
    'summary': 'QWeb PDF reports: IPC certificates, subcontracts, work orders',
    'description': """
PDF Reports for Buruuj Construction
====================================
* Interim Payment Certificate (Client + Subcontractor) — formal payment certificate
  with line items, retention, advance recovery, and signature blocks
* Subcontract Agreement — branded contract document with parties, scope,
  financial terms, schedule, bonds, LD, and BOQ
* Work Order — issuance document with subcontract reference, scope, value, sign-off
""",
    'author': 'Buruuj Construction Co.',
    'license': 'OPL-1',
    'depends': ['buruuj_ipc', 'buruuj_subcontractor'],
    'data': [
        'reports/report_paperformat.xml',
        'reports/report_actions.xml',
        'reports/report_ipc.xml',
        'reports/report_subcontract.xml',
        'reports/report_workorder.xml',
    ],
    'installable': True,
    'application': False,
}
