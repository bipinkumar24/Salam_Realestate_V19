# -*- coding: utf-8 -*-
{
    'name': 'Salaam Developer & Contractor Contracts',
    'version': '19.0.1.0.0',
    'category': 'Real Estate / Finance',
    'summary': 'Manages Sale, Istisna, Ijara, Musharaka, Subcontractor, and Consultancy contracts for Salaam Investment Bank real estate projects — Sharia-compliant.',
    'description': """
Salaam Developer & Contractor Contracts
========================================
New standalone module for IAFAO — Investment Appraisal and Final Approval Office.

Contract Types:
- Sale Contract (عقد البيع)
- Istisna Construction Finance (عقد الاستصناع)
- Ijara Lease (عقد الإجارة)
- Diminishing Musharaka JV (عقد المشاركة المتناقصة)
- Subcontractor Agreement
- Consultancy Agreement

Integrates with:
- bank_realestate_collab (BRE applications, property.details)
- rental_management (rent contracts)
- Odoo Invoicing (milestone-based payment schedules)
    """,
    'author': 'Salaam Investment Bank — IAFAO',
    'website': 'https://salaambank.com',
    'depends': [
        'base',
        'mail',
        'account',
        'bank_realestate_collab',
        'rental_management',
    ],
    'data': [
        # Security
        'security/dev_contracts_groups.xml',
        'security/ir.model.access.csv',
        # Data
        'data/dev_contract_sequence.xml',
        'data/dev_clause_data.xml',
        # Views — base first
        'views/dev_contract_base_views.xml',
        'views/dev_contract_clause_views.xml',
        'views/dev_contract_milestone_views.xml',
        'views/dev_contract_sale_views.xml',
        'views/dev_contract_istisna_views.xml',
        'views/dev_contract_ijara_views.xml',
        'views/dev_contract_musharaka_views.xml',
        'views/dev_contract_subcontractor_views.xml',
        'views/dev_contract_consultancy_views.xml',
        'views/dev_contracts_menu.xml',
        # Reports
        'report/dev_contract_report.xml',
        'report/dev_contract_report_templates.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
