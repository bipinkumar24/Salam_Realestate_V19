# -*- coding: utf-8 -*-
{
    'name': 'Property Investment Appraisal',
    'version': '19.0.1.0.0',
    'category': 'Real Estate / Finance',
    'summary': 'Individual Investment Proposal — Five Cs Credit Appraisal',
    'description': """
        Property Investment Appraisal Module for Odoo 19
        =================================================
        Implements the Individual Investment Proposal workflow covering:
        - Character (5%): Applicant personal profile
        - Condition (5%): Employment & business details
        - Capital (15%): Personal assets & liabilities
        - Capacity (50%): Monthly income & expenses / IIR
        - Collateral (25%): Investment security valuation
    """,
    'author': 'Property Management',
    'depends': [
        'base',
        'mail',
        'account',
    ],
    'data': [
        'security/groups.xml',
        'security/ir.model.access.csv',
        'data/ir_sequence.xml',
        'data/sector_data.xml',
        'views/investment_application_views.xml',
        'views/investment_collateral_views.xml',
        'views/investment_liability_views.xml',
        'views/sector_views.xml',
        'views/menu.xml',
        'report/investment_proposal_report.xml',
        'report/investment_proposal_template.xml',
    ],
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}
