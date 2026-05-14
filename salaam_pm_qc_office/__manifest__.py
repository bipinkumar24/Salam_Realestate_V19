{
    "name": "Salaam PM / QC Office",
    "summary": "Inspection & Test Plan (ITP) and Inspection & Test Report "
               "(ITR) registry for the Project Management / Quality Control office.",
    "description": """
Salaam PM / QC Office
=====================

Holds the ITP / ITR template library that drives field inspection
work on Salaam construction lots. Pre-Launch Readiness items can
reference an ITP template through the generic Reference field on
``salaam.readiness.item`` to assert that the required inspection
artefact is loaded before mobilization.
""",
    "author": "Salaam Investment Bank - IAFAO",
    "website": "https://salaambank.com",
    "category": "Salaam/Project Governance",
    "version": "19.0.1.0.0",
    "license": "LGPL-3",
    "depends": ["base", "web", "mail", "salaam_iafao_dashboard"],
    "data": [
        "security/ir.model.access.csv",
        "views/itp_template_views.xml",
        "views/pm_qc_menu.xml",
    ],
    "application": False,
    "installable": True,
    "auto_install": False,
}
