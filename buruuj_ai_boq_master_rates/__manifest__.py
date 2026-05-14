# -*- coding: utf-8 -*-
{
    'name': 'AI BOQ — Buruuj Master Rates Bridge',
    'version': '19.0.1.0.0',
    'category': 'Construction',
    'summary': 'Re-price AI-generated BOQ lines from the Buruuj master rate database',
    'depends': ['ai_boq_reader_v19', 'buruuj_tendering'],
    'data': [
        'views/boq_project_views.xml',
    ],
    'license': 'LGPL-3',
    'installable': True,
    'application': False,
}
