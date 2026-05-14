# -*- coding: utf-8 -*-
{
    "name": "Salaam Pre-Launch Readiness (IAFAO)",
    "summary": "Phase-1 Lot-1 readiness tracker (14 categories, 110 items) "
               "driving Decision Gate 0 / Mobilization Approval.",
    "description": """
Salaam Pre-Launch Readiness Tracker
===================================

Live replacement for the IAFAO Phase-1 Lot-1 Pre-Launch Readiness
spreadsheet. Tracks 110 items across 14 categories (A-N) and computes
the binding Go/No-Go signal for vertical construction start.

Gate logic
----------
* Hard Gate (A, B, C, D, F, G, M)  ->  must be 100% complete
* Parallel  (E, H, I, J, K, L)     ->  must be at least 80% complete
* Mobilization (N)                  ->  must be 100% by Day-1

When all three thresholds are met simultaneously the tracker reports
``Ready to Mobilize`` and posts evidence on the linked Decision Gate 0
record (in salaam_execution_plan).

Key features
------------
* Three-model design: tracker > category > item
* Reference field on each item for cross-module linking (ITP, contract,
  HSE plan, fatwa, etc.) -- the integration backbone
* Live KPIs computed nightly via cron and surfaced into the IAFAO
  dashboard
* Excel import wizard for tenants migrating from the spreadsheet
* Full chatter, activities, and 3-tier security (user / officer / manager)

IAFAO  -  Salaam Real Estate  -  CONFIDENTIAL
""",
    "author": "Salaam Investment Bank - IAFAO",
    "website": "https://salaambank.com",
    "category": "Salaam/Project Governance",
    "version": "19.0.1.1.0",
    "license": "LGPL-3",
    "depends": [
        # Core
        "base",
        "web",
        "mail",
        # Salaam platform - install order
        "bank_realestate_collab",
        "salaam_iafao_dashboard",
        "salaam_execution_plan",
        "salaam_pm_qc_office",
        "salaam_hse",
        "salaam_reservation",
        "salaam_procurement",
        "salaam_contractor_mgmt",
        "salaam_dev_contracts",
    ],
    "data": [
        # Security first
        "security/readiness_security.xml",
        "security/ir.model.access.csv",
        # Data seed
        "data/readiness_seed.xml",
        "data/ir_cron.xml",
        # Views
        "views/readiness_item_views.xml",
        "views/readiness_category_views.xml",
        "views/readiness_tracker_views.xml",
        "views/readiness_snapshot_views.xml",
        "wizard/readiness_excel_import_views.xml",
        "wizard/readiness_clone_wizard_views.xml",
        # Reports
        "report/readiness_evidence_pack.xml",
        # Menu last
        "views/readiness_menu.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "salaam_prelaunch_readiness/static/src/css/readiness.css",
        ],
    },
    "application": True,
    "installable": True,
    "auto_install": False,
}
