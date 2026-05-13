# -*- coding: utf-8 -*-
{
    'name': 'Expense Requests',
    'summary': 'Multi-level expense request approval on vendor bills',
    'description': 'Expense request workflow with department, HR, finance and GM approvals.',
    'website': 'http://www.yourcompany.com',
    'category': 'Accounting',
    'version': '19.0.1.0.0',
    'license': 'LGPL-3',
    'depends': ['base', 'account', 'sale', 'hr', 'mail'],
    'data': [
        'security/ir.model.access.csv',
        'security/security.xml',
        'wizard/remark_view.xml',
        'views/account.xml',
        'views/approval_level_account_view.xml',
    ],
    'demo': [
        'demo/demo.xml',
    ],
    'installable': True,
    'application': False,
}
