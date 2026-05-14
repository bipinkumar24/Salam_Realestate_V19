# -*- coding: utf-8 -*-
{
    'name': 'Buruuj Construction - Tendering & BOQ',
    'version': '19.0.1.0.0',
    'category': 'Construction',
    'summary': 'Tendering, Bill of Quantities, estimation, and bid management',
    'description': """
Tendering & BOQ
================
* Tender / Opportunity pipeline with deadlines and reminders
* Bill of Quantities (BOQ) builder — hierarchical sections and line items
* Master rate database (labor, material, equipment, subcontractor)
* Rate analysis with wastage and overhead/profit markup
* Bid submission and tender comparison
* Award conversion: winning bid → project + frozen baseline budget
""",
    'author': 'Buruuj Construction Co.',
    'license': 'OPL-1',
    'depends': ['buruuj_base', 'mail', 'product', 'project'],
    'data': [
        'security/ir.model.access.csv',
        'views/buruuj_rate_views.xml',
        'views/buruuj_tender_views.xml',
        'wizards/boq_import_wizard_views.xml',
        'views/buruuj_boq_views.xml',
        'views/buruuj_tendering_menus.xml',
    ],
    'installable': True,
    'application': False,
}
