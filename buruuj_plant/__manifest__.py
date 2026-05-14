# -*- coding: utf-8 -*-
{
    'name': 'Buruuj Construction - Plant & Equipment',
    'version': '19.0.1.0.0',
    'category': 'Construction',
    'summary': 'Equipment register, allocation, fuel logs, and PM schedules',
    'description': """
Plant & Equipment
==================
* Equipment register with ownership and rental status
* Project allocation with internal hire rates → project P&L
* Preventive maintenance schedule and breakdown logs
* Fuel logs and operator logs
* Rental tracking with off-hire dates
""",
    'author': 'Buruuj Construction Co.',
    'license': 'OPL-1',
    'depends': ['buruuj_base', 'buruuj_project', 'mail'],
    'data': [
        'security/ir.model.access.csv',
        'views/buruuj_plant_views.xml',
        'views/buruuj_plant_menus.xml',
    ],
    'installable': True,
    'application': False,
}
