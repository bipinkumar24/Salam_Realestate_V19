{
    'name': "custom_real_estate",
    'category': 'CRM',
    'version': '19.0.1.0.0',
    'author': 'Salam Smart Solutions',
    'summary': 'Custom Salam Real Estate',
    'description': "",
    'depends': [
        'base', 'crm', 'sale', 'rental_management'
    ],
    'data': [
        'security/ir.model.access.csv',
        'security/secuirity.xml',
        'wizard/craete_booking_wizard_view.xml',
        'wizard/crm_booking_wizard_view.xml',
        'wizard/remark_view.xml',
        'views/approval_level_crm_view.xml',
        'views/crm_lead.xml',
        'views/areas_view.xml',
        'views/rooms.xml',
        'views/unit_prioritization_view.xml',

    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
