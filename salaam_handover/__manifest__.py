# -*- coding: utf-8 -*-
{
    'name': 'Salaam Handover — Snagging, Unit Completion & Warranty',
    'version': '19.0.1.0.0',
    'summary': 'Room-by-room snagging, handover certificates, DLP warranty claims — Salaam City',
    'description': """
salaam_handover
===============
Covers the full post-construction handover chain for Salaam City (1,600 units):

Models:
-------
1. salaam.snag.list
   Master snagging record per unit per inspection round.
   Status: draft -> in_progress -> contractor_response -> re_inspection -> closed
   Room-by-room punch list items with defect classification, photo attachment,
   trade responsibility, and rectification deadline.

2. salaam.snag.item
   Individual defect item within a snag list.
   Status: open -> contractor_notified -> rectified -> verified / rejected
   Category: structural / MEP / finishes / external / common_area / other
   Severity: critical / major / minor / cosmetic

3. salaam.handover.certificate
   Formal unit handover document.
   Generated only when all snag items are verified closed.
   Links buyer, unit, sale contract, snag list, key release.
   Status: draft -> issued -> signed -> registered

4. salaam.warranty.claim
   Post-handover defect claim during Defect Liability Period (DLP).
   Distinguishes warranty (contractor cost) from maintenance (owner cost).
   Status: open -> assessed -> contractor_notified -> rectified -> closed
   Links to original snag list and handover certificate.
   DLP expiry tracked per unit from handover_date.
""",
    'author': 'Salaam Investment Bank — IAFAO',
    'category': 'Construction',
    'license': 'LGPL-3',
    'depends': [
        'base', 'mail',
        'salaam_construction_mgmt',
        'salaam_dev_contracts',
        'rental_management',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/sequences.xml',
        'views/snag_list_views.xml',
        'views/snag_item_views.xml',
        'views/handover_certificate_views.xml',
        'views/warranty_claim_views.xml',
        'views/property_inherit_views.xml',
        'views/menus.xml',
        'report/handover_certificate_report.xml',
        'report/snag_list_report.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
