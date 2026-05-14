# -*- coding: utf-8 -*-
{
    'name': 'Buruuj Construction - HSE',
    'version': '19.0.1.0.0',
    'category': 'Construction',
    'summary': 'Toolbox talks, permits to work, incidents, PPE',
    'description': """
Health, Safety & Environment
=============================
* Toolbox Talks with attendee acknowledgement
* Permit to Work (hot work, confined space, work at height)
* Incident & Near-miss reporting with root cause
* PPE issuance tracking
""",
    'author': 'Buruuj Construction Co.',
    'license': 'OPL-1',
    'depends': ['buruuj_base', 'buruuj_project', 'mail'],
    'data': [
        'security/ir.model.access.csv',
        'views/buruuj_hse_views.xml',
        'views/buruuj_hse_menus.xml',
    ],
    'installable': True,
    'application': False,
}
