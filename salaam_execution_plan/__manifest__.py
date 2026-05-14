{
    "name": "Salaam Execution Plan",
    "summary": "Phase / Lot execution plan with Decision Gate records.",
    "description": """
Salaam Execution Plan
=====================

Defines the project execution plan structure:

* Phase  (e.g. Phase 1 - Vertical Construction)
* Lot    (e.g. Lot 1 - Tower A foundations)
* Decision Gate  (Gate 0 mobilization approval, Gate 1, Gate 2 ...)

The Decision Gate record is the target of Pre-Launch Readiness
evidence: when the readiness tracker reports ``Ready to Mobilize``,
it posts a message and attaches the immutable snapshot to the
linked Decision Gate record.
""",
    "author": "Salaam Investment Bank - IAFAO",
    "website": "https://salaambank.com",
    "category": "Salaam/Project Governance",
    "version": "19.0.1.0.0",
    "license": "LGPL-3",
    "depends": ["base", "web", "mail", "salaam_iafao_dashboard"],
    "data": [
        "security/ir.model.access.csv",
        "views/execution_plan_views.xml",
        "views/decision_gate_views.xml",
        "views/execution_menu.xml",
    ],
    "application": False,
    "installable": True,
    "auto_install": False,
}
