# -*- coding: utf-8 -*-
{
    'name': 'Bank & Real Estate Collaboration Platform',
    'version': '19.0.1.0.1',
    'category': 'Real Estate / Finance',
    'summary': 'Integrated platform for Bank and Real Estate collaboration with Sharia-compliant financing',
    'description': """
        Integrated Odoo Platform for Bank & Real Estate Collaboration
        ==============================================================
        Features:
        - Real Estate Agent & Bank Officer role management
        - Customer onboarding with Sharia compliance
        - Bank approval workflow (pending → under review → approved/rejected)
        - Document attachment management
        - Real-time status tracking
        - Dashboards & reports for both entities
    """,
    'author': 'Custom Development',
    'website': '',
    'depends': [
        'base',
        'mail',
        'portal',
        'web',
        'board',
        'contacts',
        'crm',
        'rental_management',
        'custom_real_estate',
        'property_investment_appraisal',
    ],
    'data': [
        # Security
        'security/security.xml',
        'security/ir.model.access.csv',

        # Data
        'data/sequence_data.xml',
        'data/stage_data.xml',

        # Views
        'views/property_views.xml',
        'views/customer_application_views.xml',
        'views/financing_request_views.xml',
        'views/document_views.xml',
        'views/dashboard_views.xml',
        'views/appraisal_integration_views.xml',
        'views/menu_views.xml',

        # Portal
        'views/templates/portal_templates.xml',

        # Website
        'views/templates/website_homepage.xml',

        # Reports
        'report/application_report.xml',
        'report/report_templates.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'bank_realestate_collab/static/src/css/main.css',
            'bank_realestate_collab/static/src/js/dashboard.js',
        ],
        'web.assets_frontend': [
            'bank_realestate_collab/static/src/css/portal.css',
            'bank_realestate_collab/static/src/js/portal_app.js',
        ],
    },
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
    'pre_init_hook': 'pre_init_hook',
    # 'post_init_hook': 'post_init_hook',
}
