# -*- coding: utf-8 -*-
{
    "name": "Buruuj Construction - Cost Control",
    "version": "19.0.1.0.0",
    "category": "Construction",
    "summary": "Project cost ledger: budget vs committed vs actual, S-curve, EVM, variance analysis",
    "description": """
Cost Control & Project P&L
============================
Consolidates costs from every other Buruuj module into a single project cost ledger.

Features:
* **Cost Breakdown Structure (CBS)** per project - hierarchical budget categories
* **Three-number tracking** per CBS line: Budget / Committed / Actual
* **Forecast at Completion** (FAC) = Actual + outstanding commitments + estimate to complete
* **Time-phased budget** producing planned vs actual S-curve
* **Earned Value Metrics**: BCWS, BCWP, ACWP, CPI, SPI, CV, SV
* **Variance log** with cause codes and corrective actions
* **Auto-feeds** from procurement (POs, GRNs, issuances), subcontracts (IPCs, work orders),
  rental (contracts), plant (allocations), back-charges
* **Project P&L view** showing contract value, revised budget, costs to date, forecast,
  margin movement
* **Cost Officer** role with restricted edit rights to baseline budget

Manual journal entries supported for indirect costs, head office overheads, etc.
""",
    "author": "Buruuj Construction Co.",
    "license": "OPL-1",
    "depends": [
        "buruuj_base",
        "buruuj_project",
        "buruuj_subcontractor",
        "buruuj_ipc",
        "buruuj_plant",
        "buruuj_rental",
        "buruuj_procurement",
        "mail",
    ],
    "data": [
        "security/buruuj_cost_control_security.xml",
        "security/ir.model.access.csv",
        "data/ir_sequence_data.xml",
        "data/buruuj_cost_category_data.xml",
        "data/buruuj_variance_cause_data.xml",
        "data/ir_cron_data.xml",
        "views/buruuj_cost_category_views.xml",
        "views/buruuj_variance_cause_views.xml",
        "views/buruuj_cbs_views.xml",
        "views/buruuj_cost_entry_views.xml",
        "views/buruuj_variance_views.xml",
        "views/buruuj_project_pnl_views.xml",
        "views/buruuj_evm_views.xml",
        "views/buruuj_cost_control_menus.xml",
    ],
    "installable": True,
    "application": False,
}
