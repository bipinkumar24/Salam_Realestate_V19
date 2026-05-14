# -*- coding: utf-8 -*-
{
    "name": "Buruuj Construction - Customer & Subcontractor Portal",
    "version": "19.0.1.0.0",
    "category": "Construction",
    "summary": "Self-service portal for clients and subcontractors",
    "description": """
Customer & Subcontractor Portal
=================================
Extends Odoo's portal framework so external parties can self-serve.

Client portal:
* View own projects with progress, milestones, contract value
* View and digitally approve Client IPCs
* Respond to drawings issued for approval (approve / approve with comments / reject)
* View and respond to RFIs assigned to them
* View Variation Orders pending approval
* Access transmittals and project documents

Subcontractor portal:
* View own subcontracts, work orders, scorecards
* Submit own IPCs (creates draft Sub-IPC for QS review)
* Acknowledge work orders
* View back-charges raised against them with dispute flag
* View license / insurance expiry alerts
* View and acknowledge transmittals

Security:
* Each user sees only records linked to their partner
* All write operations create audit trail in chatter
* Critical state changes (IPC approval, IPC submission) are logged with user, IP, timestamp
""",
    "author": "Buruuj Construction Co.",
    "license": "OPL-1",
    "depends": [
        "buruuj_base",
        "buruuj_project",
        "buruuj_subcontractor",
        "buruuj_ipc",
        "buruuj_site_ops",
        "buruuj_quality",
        "portal",
        "mail",
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/portal_templates.xml",
        "views/portal_client_templates.xml",
        "views/portal_sub_templates.xml",
        "views/portal_menu.xml",
    ],
    "assets": {
        "web.assets_frontend": [
            "buruuj_portal/static/src/css/portal.css",
        ],
    },
    "installable": True,
    "application": False,
}
