# -*- coding: utf-8 -*-
{
    'name': 'Salaam Procurement — Tender Management & Payment Certificates',
    'version': '19.0.1.0.0',
    'summary': 'Formal tender/bid evaluation, IPC workflow, contractor payment certification',
    'description': """
salaam_procurement
==================
Covers two critical gaps in the developer-to-delivery chain:

Models:
-------
1. salaam.tender
   Tender master record per construction package.
   Types: Open / Selective / Negotiated / Framework
   Status: draft -> published -> closed -> evaluation -> awarded / cancelled
   Links: delivery method, construction project, contract package description

2. salaam.tender.invitee
   Invited tenderer record. Tracks submission status, bid amount,
   qualification status, and evaluation scores.

3. salaam.tender.evaluation
   Weighted evaluation scorecard per tenderer.
   Criteria: technical (40%), commercial (30%), Sharia compliance (15%),
   HSE (10%), local content (5%).
   Auto-ranks tenderers. Recommendation generated on save.

4. salaam.payment.certificate
   Interim Payment Certificate (IPC) workflow.
   Contractor submits monthly valuation -> QS certifies -> Client approves -> Finance pays.
   Status: draft -> submitted -> qs_review -> approved -> paid
   Tracks: gross valuation, retention (5%), previous certified, net due.
   Links to Istisna contract milestone for payment trigger.
   Cumulative certified amount tracked against contract value.
""",
    'author': 'Salaam Investment Bank — IAFAO',
    'category': 'Construction',
    'license': 'LGPL-3',
    'depends': [
        'base', 'mail',
        'salaam_construction_mgmt',
        'salaam_dev_contracts',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/sequences.xml',
        'views/tender_views.xml',
        'views/tender_evaluation_views.xml',
        'views/payment_certificate_views.xml',
        'views/project_inherit_views.xml',
        'views/menus.xml',
        'report/tender_report.xml',
        'report/ipc_report.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
