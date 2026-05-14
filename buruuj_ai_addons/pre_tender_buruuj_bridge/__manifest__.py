# -*- coding: utf-8 -*-
{
    'name': 'Pre-Tender ↔ Buruuj Tendering Bridge',
    'version': '19.0.1.0.0',
    'category': 'Sales/CRM',
    'summary': 'Hand-off from pre-tender opportunity to BOQ-based tender estimation',
    'description': """
Bridge: Pre-Tender ↔ Buruuj Tendering
=====================================
Links the pre-tender lifecycle (crm.lead extension) to the construction
tendering / BOQ workflow (buruuj.tender).

Adds:
* Forward conversion: kickoff-stage opportunity → buruuj.tender record with
  inherited client, deadline, estimated value and reference back to the
  originating opportunity.
* Backward link: smart button on buruuj.tender to open the originating
  pre-tender opportunity (compliance, capture, risks, stakeholders).
* State mirroring: buruuj.tender state changes propagate to the opportunity
  (submitted, won, lost) — the Tier 1 gate is enforced before "won".

This is a glue module. Both pre_tender_management and buruuj_tendering remain
installable on their own.
""",
    'author': 'Buruuj',
    'license': 'LGPL-3',
    'depends': [
        'pre_tender_management',
        'buruuj_tendering',
    ],
    'data': [
        'views/crm_lead_views.xml',
        'views/buruuj_tender_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': True,
}
