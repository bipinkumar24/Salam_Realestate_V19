# -*- coding: utf-8 -*-
{
    'name': 'Salaam Construction & Governance Management',
    'version': '19.0.1.0.0',
    'category': 'Real Estate / Construction',
    'summary': (
        'End-to-end construction project management and corporate governance '
        'document management for Salaam Investment Bank real estate developments. '
        'Links Istisna contracts → construction projects, subcontractors → tasks, '
        'tracks budgets, drawings, site progress reports, and governance documents.'
    ),
    'author': 'Salaam Investment Bank — IAFAO',
    'website': 'https://salaambank.com',
    'depends': [
        'base',
        'mail',
        'account',
        'project',
        'salaam_dev_contracts',
        'bank_realestate_collab',
        'rental_management',
    ],
    'data': [
        # Security
        'security/construction_groups.xml',
        'security/ir.model.access.csv',
        # Data
        'data/construction_sequences.xml',
        'data/construction_stages.xml',
        'data/governance_doc_types.xml',
        # Views — models first
        'views/construction_project_views.xml',
        'views/construction_phase_views.xml',
        'views/construction_task_views.xml',
        'views/budget_line_views.xml',
        'views/site_report_views.xml',
        'views/drawing_register_views.xml',
        'views/governance_document_views.xml',
        'views/construction_menu.xml',
        # Reports
        'report/site_report_template.xml',
        'report/budget_report_template.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
