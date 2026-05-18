# -*- coding: utf-8 -*-
{
    'name': 'Buruuj Construction - IPC & Billing',
    'version': '19.0.1.0.0',
    'category': 'Construction',
    'summary': 'Interim Payment Certificates for clients and subcontractors',
    'description': """
IPC & Billing
==============
* Client IPC: Interim Payment Certificate to bill the client
* Subcontractor IPC: Interim Payment Certificate from the subcontractor
* Retention, advance recovery, materials on site
* Mirrored approval workflow (QS → PM → Finance)
""",
    'author': 'Buruuj Construction Co.',
    'license': 'OPL-1',
    'depends': ['buruuj_subcontractor', 'buruuj_project',
                'buruuj_tendering', 'mail'],
    'data': [
        'security/ir.model.access.csv',
        'views/buruuj_ipc_views.xml',
        'views/buruuj_ipc_menus.xml',
    ],
    'installable': True,
    'application': False,
}
