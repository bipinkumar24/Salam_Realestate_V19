# -*- coding: utf-8 -*-
{
    'name': 'Buruuj Construction - Contract Management',
    'version': '19.0.1.0.0',
    'category': 'Construction',
    'summary': 'Master contracts, key dates, bonds, claims (EOT, prolongation)',
    'description': """
Contract Management
====================
* Master contract repository (client, sub, supply, lease)
* Key date tracking with proactive alerts
* Bonds and insurance expiry monitoring
* Claims management (EOT, prolongation cost)
""",
    'author': 'Buruuj Construction Co.',
    'license': 'OPL-1',
    'depends': ['buruuj_base', 'buruuj_project', 'mail'],
    'data': [
        'security/ir.model.access.csv',
        'views/buruuj_contract_views.xml',
        'views/buruuj_contract_menus.xml',
    ],
    'installable': True,
    'application': False,
}
