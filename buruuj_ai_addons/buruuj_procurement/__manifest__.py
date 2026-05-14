# -*- coding: utf-8 -*-
{
    "name": "Buruuj Construction - Procurement & Inventory",
    "version": "19.0.1.0.0",
    "category": "Construction",
    "summary": "Material requisitions, RFQs, purchase orders, GRNs, project store inventory",
    "description": """
Procurement & Inventory
========================
End-to-end materials workflow for construction projects:

* **Material Master** — register of materials with codes, UoM, default specifications
* **Material Requisition (MR)** — site requests material with quantity, required-by date, BOQ link
* **Request for Quotation (RFQ)** — to multiple vendors with comparative table
* **Purchase Order (PO)** — to selected vendor with approval workflow (QS → PM → Director)
* **Goods Receipt Note (GRN)** — quality check on receipt with accept/reject and short-supply tracking
* **Material Issuance** — from store to work with project / phase / WBS allocation
* **Project Stock** — real-time balance per material per project store

Distinct from Odoo core `purchase` module — uses construction-specific approval roles
and connects directly to BOQ lines, project phases, and subcontract back-charges.
""",
    "author": "Buruuj Construction Co.",
    "license": "OPL-1",
    "depends": [
        "buruuj_base",
        "buruuj_project",
        "buruuj_subcontractor",
        "mail",
        "uom",
    ],
    "data": [
        "security/ir.model.access.csv",
        "data/ir_sequence_data.xml",
        "data/buruuj_material_category_data.xml",
        "views/buruuj_material_views.xml",
        "views/buruuj_mr_views.xml",
        "views/buruuj_rfq_views.xml",
        "views/buruuj_po_views.xml",
        "views/buruuj_grn_views.xml",
        "views/buruuj_issuance_views.xml",
        "views/buruuj_stock_views.xml",
        "views/buruuj_procurement_menus.xml",
    ],
    "installable": True,
    "application": False,
}
