# -*- coding: utf-8 -*-
{
    'name': 'KYC Dual-List Screening — BRE Platform',
    'version': '19.0.3.0.0',
    'summary': 'KYC/AML screening via external KYC Dual-List Server (Watchlist + Approved List).',
    'description': """
KYC Dual-List Screening
========================
Calls the external KYC Dual-List Server which screens applicants against:
  LIST 1 — Watchlist  : sanctions, defaults, fraud → status: hit
  LIST 2 — Approved   : bank pre-vetted clients    → status: pre_approved

Outcome matrix:
  No hit + No approved match  → cleared
  No hit + Approved match     → pre_approved (green)
  Watchlist hit               → hit (officer review — overrides approved)

Configuration: Settings → KYC / AML Watchlist → enter server URL and API key.
The server itself handles Google Drive / Dropbox sync for both lists.
    """,
    'author': 'Salaam Investment Bank — IAFAO',
    'category': 'Banking / Compliance',
    'license': 'LGPL-3',
    'depends': [
        'bank_realestate_collab',
        'base_setup',
    ],
    'data': [
        'views/kyc_views.xml',
        'security/ir.model.access.csv',
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
}
