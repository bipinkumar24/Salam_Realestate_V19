{
    "name": "Salaam IAFAO Dashboard",
    "summary": "Root menu and dashboard container for Salaam IAFAO platform modules.",
    "description": """
Salaam IAFAO Dashboard
======================

Provides the root IAFAO menu and a lightweight dashboard model that
downstream Salaam platform modules (Pre-Launch Readiness, Execution
Plan, PM/QC Office, etc.) hang their menus and KPIs from.

This is a foundation module: no business logic, just the navigation
anchor and a placeholder dashboard record so other modules can post
KPIs against a stable target.
""",
    "author": "Salaam Investment Bank - IAFAO",
    "website": "https://salaambank.com",
    "category": "Salaam/Project Governance",
    "version": "19.0.1.0.0",
    "license": "LGPL-3",
    "depends": ["base", "web", "mail"],
    "data": [
        "security/ir.model.access.csv",
        "views/iafao_dashboard_views.xml",
        "views/iafao_menu.xml",
    ],
    "application": True,
    "installable": True,
    "auto_install": False,
}
