# -*- coding: utf-8 -*-
{
    "name": "Buruuj Construction - Equipment Rental",
    "version": "19.0.1.0.0",
    "category": "Construction",
    "summary": "Equipment rental contracts, requisitions, off-hire, timesheet, vendor invoice reconciliation",
    "description": """
Equipment Rental Management
============================
Manages equipment rented from third-party vendors (rental-in) with full
lifecycle from requisition to invoice reconciliation.

Workflow:
1. Site Engineer raises a Rental Requisition
2. Procurement quotes from rental vendors
3. Rental Contract issued (daily/weekly/monthly rates, mob/demob, idle clause)
4. Equipment arrives, daily timesheet captured (working vs idle hours)
5. Off-hire decision (auto-alerts when project no longer needs equipment)
6. Vendor invoice reconciled against captured timesheet
7. Disputes tracked separately

Distinct from buruuj_plant (which manages owned equipment) and buruuj_tools
(which manages small tools).
""",
    "author": "Buruuj Construction Co.",
    "license": "OPL-1",
    "depends": ["buruuj_base", "buruuj_project", "buruuj_plant",
                "buruuj_tendering", "mail"],
    "data": [
        "security/ir.model.access.csv",
        "data/ir_sequence_data.xml",
        "data/ir_cron_data.xml",
        "views/buruuj_rental_requisition_views.xml",
        "views/buruuj_rental_contract_views.xml",
        "views/buruuj_rental_timesheet_views.xml",
        "views/buruuj_rental_invoice_views.xml",
        "views/buruuj_rental_menus.xml",
    ],
    "installable": True,
    "application": False,
}
