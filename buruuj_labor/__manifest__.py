# -*- coding: utf-8 -*-
{
    "name": "Buruuj Construction - Labor & Productivity",
    "version": "19.0.1.0.0",
    "category": "Construction",
    "summary": "Site workforce, attendance, timesheets, wage runs, productivity",
    "description": """
Labor & Productivity
=====================
Site labor cost capture for project cost control.

* **Workforce Register** — workers (own + subcontractor labor) with trade,
  rates, certifications
* **Daily Attendance** — quick capture at site by foreman or storekeeper
* **Timesheet** — hours per worker per day per project per WBS phase
* **Productivity** — output (m3, m2, kg) per crew per day; hours per unit
* **Allowances & Deductions** — overtime, transport, accommodation, advances,
  fines
* **Wage Runs** — weekly or monthly per project
* **Cost Ledger Feed** — auto-creates buruuj.cost.entry records so labor
  flows into the project P&L

Distinct from Odoo HR/Payroll — focused on construction site operations and
project costing. For full payroll (GOSI, statutory deductions, payslips,
bank files), Odoo's Payroll module can be installed alongside.
""",
    "author": "Buruuj Construction Co.",
    "license": "OPL-1",
    "depends": [
        "buruuj_base",
        "buruuj_project",
        "buruuj_subcontractor",
        "buruuj_tendering",
        "buruuj_cost_control",
        "hr",
        "mail",
    ],
    "data": [
        "security/ir.model.access.csv",
        "data/ir_sequence_data.xml",
        "data/buruuj_labor_trade_data.xml",
        "data/buruuj_allowance_type_data.xml",
        "views/buruuj_worker_views.xml",
        "views/buruuj_attendance_views.xml",
        "views/buruuj_timesheet_views.xml",
        "views/buruuj_wage_run_views.xml",
        "views/buruuj_productivity_views.xml",
        "views/buruuj_labor_master_data_views.xml",
        "views/buruuj_labor_menus.xml",
    ],
    "installable": True,
    "application": False,
}
