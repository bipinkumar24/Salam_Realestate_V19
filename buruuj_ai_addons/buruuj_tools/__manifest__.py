# -*- coding: utf-8 -*-
{
    'name': 'Buruuj Construction - Tool Management',
    'version': '19.0.1.0.0',
    'category': 'Construction',
    'summary': 'Tool register, issuance, calibration, transfers, loss/damage',
    'description': """
Construction Tool Management
=============================
Manages small tools and instruments distinct from heavy plant:
* Tool register with categories (power tools, hand tools, instruments,
  scaffolding, formwork, safety equipment)
* Tool issuance to workers with check-out / check-in workflow and
  condition rating each way
* Calibration schedule for instruments with certificate tracking
* Tool transfer between sites with handover signature
* Loss / damage register with cost recovery
* Consumables tracking (issued vs. returned)
* Mobile-friendly views for storekeepers

Distinct from buruuj_plant which handles heavy plant and vehicles.
""",
    'author': 'Buruuj Construction Co.',
    'license': 'OPL-1',
    'depends': ['buruuj_base', 'buruuj_project', 'mail', 'hr'],
    'data': [
        'security/ir.model.access.csv',
        'data/ir_sequence_data.xml',
        'data/buruuj_tool_category_data.xml',
        'views/buruuj_tool_category_views.xml',
        'views/buruuj_tool_views.xml',
        'views/buruuj_tool_issuance_views.xml',
        'views/buruuj_tool_transfer_views.xml',
        'views/buruuj_tool_calibration_views.xml',
        'views/buruuj_tool_loss_views.xml',
        'views/buruuj_tools_menus.xml',
    ],
    'installable': True,
    'application': False,
}
