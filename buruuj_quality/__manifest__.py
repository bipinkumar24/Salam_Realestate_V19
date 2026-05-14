# -*- coding: utf-8 -*-
{
    'name': 'Buruuj Construction - Quality & Document Control',
    'version': '19.0.1.0.0',
    'category': 'Construction',
    'summary': 'Drawing register, transmittals, material submittals',
    'description': """
Quality & Document Control
===========================
* Drawing register with revision control
* Transmittal log to consultants/clients
* Material approval submittals
""",
    'author': 'Buruuj Construction Co.',
    'license': 'OPL-1',
    'depends': ['buruuj_base', 'buruuj_project', 'mail'],
    'data': [
        'security/ir.model.access.csv',
        'views/buruuj_quality_views.xml',
        'views/buruuj_quality_menus.xml',
    ],
    'installable': True,
    'application': False,
}
