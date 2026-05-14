# -*- coding: utf-8 -*-
{
    'name': 'Buruuj Construction - Base',
    'version': '19.0.1.0.0',
    'category': 'Construction',
    'summary': 'Foundation module for Buruuj 360° Construction Management Suite',
    'description': """
Buruuj Construction - Base Module
==================================
Provides shared models, security groups, sequences, and configuration
used across all Buruuj construction modules.

Includes:
* Construction company configuration
* Common reference data (trades, work types, units of measure extensions)
* Shared security groups (PM, QS, Site Engineer, Storekeeper, HSE Officer, Director)
* Sequence definitions
* Construction-specific partner extensions
""",
    'author': 'Buruuj Construction Co.',
    'website': 'https://www.buruuj.example',
    'license': 'OPL-1',
    'depends': [
        'base',
        'mail',
        'contacts',
        'product',
        'uom',
    ],
    'data': [
        'security/buruuj_security.xml',
        'security/ir.model.access.csv',
        'data/ir_sequence_data.xml',
        'data/buruuj_trade_data.xml',
        'views/res_config_settings_views.xml',
        'views/buruuj_trade_views.xml',
        'views/res_partner_views.xml',
        'views/buruuj_menus.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}
