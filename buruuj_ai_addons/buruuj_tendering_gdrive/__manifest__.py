# -*- coding: utf-8 -*-
{
    'name': 'Buruuj Tendering — Drive Sync & Claude',
    'version': '19.0.1.1.0',
    'category': 'Construction',
    'summary': 'Push/pull Master Rates with Google Drive, plus Claude-driven rate generation',
    'depends': ['buruuj_tendering'],
    'data': [
        'security/ir.model.access.csv',
        'data/ir_cron.xml',
        'views/buruuj_gdrive_setup_views.xml',
        'views/buruuj_rate_claude_views.xml',
        'views/buruuj_rate_views.xml',
    ],
    'external_dependencies': {
        'python': ['googleapiclient', 'openpyxl', 'anthropic'],
    },
    'license': 'OPL-1',
    'installable': True,
    'application': False,
}
