# -*- coding: utf-8 -*-
{
    'name': 'Salaam Off-Plan Reservation',
    'version': '19.0.1.1.0',
    'summary': 'Reservation agreements, deposit tracking, cooling-off, expiry, BRE auto-conversion',
    'description': """
salaam_reservation
==================
Fills the gap between unit selection and full financing application
for off-plan developments (Salaam City, Djibouti).

The reservation sits on the COMMERCIAL TRACK — it does not depend
on construction progress. A customer can reserve a unit on launch day
before construction has started.

Models:
-------
1. salaam.reservation
   Master reservation record.
   Status: draft -> active -> converted / expired / cancelled
   - Reservation deposit: amount, payment method, receipt reference
   - Cooling-off period: 14 days from signing (configurable)
   - Reservation expiry: 60 days to convert to full contract (configurable)
   - On conversion: BRE application auto-created, unit -> Contracted
   - On expiry: unit returns to Available, deposit handling recorded
   - On cancellation: configurable refund policy (full / partial / forfeit)

2. salaam.reservation.payment
   Deposit payment record(s) linked to reservation.
   Supports staged payments (e.g. 2% on reservation, 8% on contract).
   Status: pending -> received -> reconciled / refunded

Property stage additions:
-------------------------
- reserved_offplan: unit reserved, reservation active
- contracted: sale contract signed, BRE approved
Under Construction, Practically Complete, Handover Ready,
Handed Over stages added to property.details via inherit.
""",
    'author': 'Salaam Investment Bank — IAFAO',
    'category': 'Real Estate',
    'license': 'LGPL-3',
    'depends': [
        'account',
        'crm',
        'base', 'mail',
        'rental_management',
        'bank_realestate_collab',
        'salaam_dev_contracts',
        'salaam_construction_mgmt',
    ],
    'data': [
        'security/ir.model.access.csv',
        'security/wizard_access.xml',
        'data/sequences.xml',
        'data/reservation_config.xml',
        'views/property_base_fallback.xml',
        'data/crm_sequences.xml',
        'views/crm_lead_base_fallback.xml',
        'views/crm_lead_views.xml',
        'views/reservation_views.xml',
        'views/project_views.xml',
        'views/bre_application_inherit_views.xml',
        'views/create_bre_application_wizard_views.xml',
        'views/reservation_payment_views.xml',
        'views/property_inherit_views.xml',
        'views/menus.xml',
        'report/reservation_form_report.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'pre_init_hook': 'pre_init_hook',
    'post_init_hook': 'post_init_hook',
    'post_migrate': 'post_migrate',
}
