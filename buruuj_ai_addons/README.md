# Buruuj Construction — Odoo 19 Addon Suite

A complete 360° Construction Management solution for **Buruuj Construction Co.**, built as a set of 11 modular Odoo 19 addons. Each module owns one functional area and depends only on the modules it strictly needs, so you can install and roll out incrementally.

---

## Module Overview

| # | Module | Purpose | Depends On |
|---|---|---|---|
| 1 | `buruuj_base` | Foundation: trades, partner extensions, security groups, sequences, top menus | `base, mail, contacts, product, uom` |
| 2 | `buruuj_tendering` | Tenders, BOQ, master rate database, award conversion | `buruuj_base` |
| 3 | `buruuj_project` | Construction project extensions: WBS, phases, variations, milestones, risks, health | `buruuj_base, buruuj_tendering, project` |
| 4 | `buruuj_subcontractor` | Subcontract lifecycle, work orders, scorecard, back-charges | `buruuj_base, buruuj_project` |
| 5 | `buruuj_ipc` | Interim Payment Certificates (client + subcontractor) with retention & advance recovery | `buruuj_subcontractor, buruuj_project` |
| 6 | `buruuj_site_ops` | Daily Progress Reports, RFIs, NCRs, snag list, ITPs (mobile-first) | `buruuj_base, buruuj_project` |
| 7 | `buruuj_plant` | Equipment register, allocations, fuel logs, maintenance | `buruuj_base, buruuj_project` |
| 8 | `buruuj_hse` | Toolbox talks, Permits to Work, incidents, PPE issuance | `buruuj_base, buruuj_project` |
| 9 | `buruuj_quality` | Drawing register, transmittals, material submittals | `buruuj_base, buruuj_project` |
| 10 | `buruuj_contract` | Master contracts, key dates, bonds, claims (EOT, prolongation) | `buruuj_base, buruuj_project` |
| 11 | `buruuj_dashboard` | CEO portfolio dashboard (cross-module KPIs) | All functional modules |
| 12 | `buruuj_reports` | QWeb PDF templates: IPC certificate, subcontract, work order | `buruuj_ipc, buruuj_subcontractor` |
| 13 | `buruuj_demo` | Realistic demo data: 3 projects, subcontractors, IPCs, DPRs, equipment | All modules above |
| 14 | `buruuj_ai` | AI drafting: BOQ from drawings, NCR from photos, subcontractor recommendations, VO drafting via Anthropic Claude | `buruuj_tendering, buruuj_project, buruuj_subcontractor, buruuj_site_ops` |
| 15 | `buruuj_tools` | Construction tool register, issuance to workers, transfers between sites, calibration tracking, loss/damage with cost recovery | `buruuj_base, buruuj_project, mail, hr` |
| 16 | `buruuj_rental` | Equipment rental requisitions, vendor contracts (daily/weekly/monthly + idle/mob/demob), daily timesheets, off-hire alerts, vendor invoice reconciliation | `buruuj_base, buruuj_project, buruuj_plant, mail` |
| 17 | `buruuj_procurement` | Material master, requisitions (site→procurement), RFQs with comparative quotation, POs with QS→PM→Director approval, GRNs with quality check, project store inventory | `buruuj_base, buruuj_project, buruuj_subcontractor, mail, uom` |
| 18 | `buruuj_cost_control` | Project cost ledger with CBS, Budget/Committed/Actual/FAC tracking, Earned Value (BCWS/BCWP/ACWP/CPI/SPI), variance log with cause codes, time-phased budget S-curve, project P&L | `buruuj_base, buruuj_project, buruuj_subcontractor, buruuj_ipc, buruuj_plant, buruuj_rental, buruuj_procurement, mail` |
| 19 | `buruuj_portal` | Customer & subcontractor self-service portal — clients view projects/IPCs/RFIs, approve client IPCs and VOs, review drawings; subs view subcontracts/work orders, submit IPCs, dispute back-charges | `buruuj_base, buruuj_project, buruuj_subcontractor, buruuj_ipc, buruuj_site_ops, buruuj_quality, portal, mail` |
| 20 | `buruuj_labor` | Workforce register, daily attendance, project timesheets, productivity tracking, wage runs with allowances/deductions, auto-feeds labor cost into the cost ledger | `buruuj_base, buruuj_project, buruuj_subcontractor, buruuj_cost_control, hr, mail` |
| 20 | `buruuj_labor` | Workforce register (own + sub labor), daily attendance, timesheets per project/phase/CBS, productivity tracking with benchmarks, wage runs with allowances/deductions, auto-feed to cost ledger | `buruuj_base, buruuj_project, buruuj_subcontractor, buruuj_cost_control, hr, mail` |
| 15 | `buruuj_tools` | Construction tool register, issuance, transfers, calibration, loss/damage with cost recovery | `buruuj_base, buruuj_project, hr` |
| 16 | `buruuj_rental` | Equipment rental contracts, requisitions, daily timesheets (working/idle), vendor invoice reconciliation, off-hire alerts | `buruuj_base, buruuj_project, buruuj_plant` |

---

## Architecture (Dependency Graph)

```
                    buruuj_base
                        │
        ┌───────────────┼─────────────────────────────┐
        │               │                             │
  buruuj_tendering   buruuj_project (extends Odoo project)
        │               │
        └──────┬────────┘
               │
        ┌──────┴─────────────┬──────────────┬──────────────┬──────────────┬──────────────┬──────────────┐
        │                    │              │              │              │              │              │
  buruuj_subcontractor  buruuj_site_ops  buruuj_plant  buruuj_hse   buruuj_quality  buruuj_contract  buruuj_dashboard
        │                                                                                                ▲
  buruuj_ipc ─────────────────────────────────────────────────────────────────────────────────────────┘
```

`buruuj_dashboard` aggregates KPIs from all functional modules.

---

## Installation

1. Drop the `buruuj_*` folders into your Odoo addons path (e.g. `/mnt/extra-addons/`).
2. Restart the Odoo server.
3. Activate Developer Mode and update the apps list.
4. Install in **dependency order** (or just install `buruuj_dashboard` and Odoo will pull the rest):

   ```
   buruuj_base
   ├── buruuj_tendering
   ├── buruuj_project
   │   ├── buruuj_subcontractor → buruuj_ipc
   │   ├── buruuj_site_ops
   │   ├── buruuj_plant
   │   ├── buruuj_hse
   │   ├── buruuj_quality
   │   └── buruuj_contract
   └── buruuj_dashboard
   ```

5. Assign users to roles (see *Security Groups* below).

### Optional add-on modules

After installing the core suite, you can selectively install:

- **`buruuj_reports`** — adds three formal PDF reports printable directly from the record forms:
  - **IPC Certificate** (Client and Subcontractor) — full payment certificate with line items, retention, advance recovery, and four-way signature block (QS, PM, Finance, Counterparty)
  - **Subcontract Agreement** — branded contract with parties, key terms, financial terms, bonds, BOQ, and standard clauses
  - **Work Order** — issuance document with subcontract reference, scope, value, and digital sign-off stamp

  All three are branded in Buruuj navy/gold and use the custom A4 paperformat. They appear automatically in the **Print** menu once the module is installed.

- **`buruuj_demo`** — bootstraps a realistic Buruuj environment for demos and training:
  - 3 clients (gov ministry, private developer, city council)
  - 2 consultants (engineering, architects)
  - 6 subcontractors covering all major trades
  - 3 active projects: Al Marina Tower (high-rise, $24.75M), Highway HC-7 ($8.2M), Government Plaza fitout ($3.1M)
  - 3 tenders (1 won → linked to Marina, 1 in submission, 1 lost for win/loss analysis)
  - 3 active subcontracts with 4 work orders
  - Sample Client IPC #5 (finance-approved) and Subcontractor IPC #3 (PM-approved)
  - DPRs, RFIs, NCRs, snags, toolbox talks, an active hot-work permit, a closed first-aid incident
  - 4 equipment items with allocations, fuel logs, maintenance
  - Drawings, transmittal, marble approval submittal
  - Master contract records, EOT claim
  - Master rate database (concrete, rebar, labor, equipment)

  Safe to install on a fresh DB — every demo record is tagged so it can be uninstalled cleanly.

- **`buruuj_ai`** — AI-powered drafting via the Anthropic Claude API:

  | Feature | Where it appears | What it does |
  |---|---|---|
  | **BOQ drafting from drawings** | Bills of Quantities → AI Drafting tab | Upload tender drawings as PDF, click Draft from Drawings. Claude analyses the document and creates structured sections with line items, UoM, estimated quantities, and trade categorisation. Auto-matches against the master rate database. Captures assumptions and missing info as a list of suggested RFIs. |
  | **NCR drafting from photos** | NCRs → AI Photo Draft tab | Site Engineer takes a photo of a defect on their phone, attaches it, clicks Draft from Photo. Claude assesses severity and drafts the description, root cause, corrective action, and preventive action. |
  | **Subcontractor recommendation** | Subcontracts → AI: Recommend Subcontractor button | When creating a new subcontract, the system pulls all subcontractors with the matching trade, builds a profile (scorecard history, current workload, license validity), and asks Claude to rank the top 3 with rationale. |
  | **VO drafting** | Variation Orders → AI Drafting tab | Paste the client's email or change request. Claude drafts the title, description, cost range, time impact, and 1-3 contractual questions to clarify before submission. |

  **Configuration**: Settings → Buruuj Construction → AI Assistant. Set the Anthropic API key, choose the default model (Opus 4.7 by default, Sonnet/Haiku for cheaper operations), set a soft monthly budget, and toggle individual features on/off.

  **Scheduled monitoring (cron jobs)**: Five automated scans run on a schedule, each independently toggleable in Settings:
  - **Daily license & insurance expiry scan** — finds subcontractors with credentials expiring within the configured window (default 30 days). Posts alerts on the partner record and creates an activity for the project PM.
  - **Daily contract key dates scan** — flags performance bonds, advance bonds, insurance, completion dates, and DLP end dates approaching expiry on active contracts.
  - **Daily overdue RFI scan** — finds RFIs past their `response_due` date. Activity reminder to the engineer who raised them, so the consultant gets chased.
  - **Weekly portfolio risk scan (AI)** — every Monday morning, gathers a snapshot of every active project (budget vs actual, schedule, NCRs, RFIs, weather hours, top risks), sends to Claude, and creates a `buruuj.portfolio.digest` record with an executive summary, top concerns by urgency, good news, and questions for PM review. Activity scheduled to all Directors.
  - **Weekly scorecard reminder** — finds active subcontracts that don't have a current-quarter scorecard yet. Reminder to the PM.

  **Audit & cost tracking**: Every AI call is logged to `buruuj.ai.task` with input/output tokens and an estimated USD cost. View at Configuration → AI Assistant → AI Task Log. Old logs (90+ days, successful) auto-clean weekly.

  **Hard boundaries — what AI is NEVER used for** (deliberate design decisions):
  - IPC calculations and approvals
  - Subcontract approval (still requires PM/Director clicking Approve)
  - HSE Permit approval
  - Incident severity for medical/lost-time injuries
  - Contract clause interpretation

  **Python dependency**: `pip install anthropic`. The module gracefully degrades if not installed — buttons hide, no errors raised on install.

- **`buruuj_tools`** — small tool and instrument management, distinct from heavy plant:

  | Feature | What it does |
  |---|---|
  | **Tool register** | Master record per tool with code, barcode, category, current location, condition, holder. Kanban grouped by location. |
  | **Categories** | Pre-loaded: Power Tools, Hand Tools, Instruments (calibration-required), Scaffolding, Formwork, Safety, Consumables. |
  | **Issuance** | Check-out a tool to a worker, set expected return, condition-out rating. On return, condition-in rating. Auto-creates a loss record if not returned. |
  | **Transfer** | Between sites with handover sign-off (from-storekeeper, to-storekeeper, condition-at-receipt). |
  | **Calibration** | For instruments. Schedule, certificate tracking, lab/cost, auto-computes next due date based on category interval. |
  | **Loss / Damage** | Lost / stolen / damaged-repairable / damaged-writeoff. Recovery via payroll deduction, subcontractor back-charge (auto-creates `buruuj.backcharge`), insurance, or write-off. |

  **Storekeeper-focused** — kanban board for the tool register and inline-editable lists for issuances and transfers make it usable on a tablet at the site store.

- **`buruuj_rental`** — equipment rental management (rental-in and rental-out):

  | Feature | What it does |
  |---|---|
  | **Requisition** | Site requests equipment. Workflow: draft → submitted → quoting → approved → contracted. PM approval required to convert to a contract. |
  | **Rental contract** | Vendor, dates, daily/weekly/monthly rates, mob/demob, idle-day rate %, fuel arrangements, operator-provided flag. Direction can be rental-in or rental-out. |
  | **Daily timesheet** | One row per day per contract. Working hours, idle hours, fuel litres, operator, remarks. Auto-computes cost (idle days at the agreed idle rate %). |
  | **Vendor invoice reconciliation** | Vendor invoice amount vs. our timesheet records for the period. Auto-computes variance. States: received → matched → (disputed) → approved → paid. Director approval required for payment. |
  | **Off-hire alerts (cron)** | Daily scan: any contract on-hire past its expected end date generates a To-Do activity for the PM. Skips if already nudged in the last 3 days. |
  | **Equipment integration** | Extends `buruuj.equipment` with rental contract history and active-rental computed field. |

  **Why this matters**: Construction companies typically leak 5-15% of project cost on rentals — equipment that stays on hire after it's needed, vendor invoices that overcharge for idle days, fuel charges that should have been on vendor account. This module makes each of those visible.

---

## Security Groups

Defined in `buruuj_base/security/buruuj_security.xml`. They are hierarchical — each implies the one above it:

| Group | Implies | Use For |
|---|---|---|
| **Site User** | `base.group_user` | General site staff with read/limited write |
| **Site Engineer** | Site User | DPRs, RFIs, NCRs, snags, ITPs |
| **Quantity Surveyor** | Site Engineer | BOQ, IPCs, variations, back-charges |
| **Project Manager** | QS | Full project, subcontract, contract control |
| **HSE Officer** | Site User | Toolbox, PTW, incidents, PPE |
| **Storekeeper** | Site User | Stock and PPE issuance |
| **Director / Executive** | PM | Read access to dashboards and approvals |
| **Construction Manager / Admin** | Director | Full admin (configuration, all data) |

---

## Key Workflows

### Tendering → Project
1. Create `buruuj.tender` → fill BOQ → review → submit → mark won.
2. Click **Convert to Project** — creates `project.project` with frozen baseline budget linked back to the tender.

### Subcontractor → IPC
1. Create `buruuj.subcontract` for a project (Draft → Approved → Signed → In Progress).
2. Issue `buruuj.workorder` records against the active subcontract.
3. Receive subcontractor IPC: create `buruuj.ipc` with `type=subcontractor`.
4. Workflow: QS → PM → Finance approval → Paid.
5. Retention is held; advance is recovered automatically per the percentages on the subcontract.

### Variation Order
1. Raise `buruuj.variation` linked to the project.
2. Submit to client → Approve → amount flows into `buruuj_revised_budget`.

### Daily Site Operations
1. Site Engineer creates a `buruuj.dpr` each day with manpower, equipment, work executed, weather.
2. Submit → PM approves.
3. Issues escalated as `buruuj.rfi`, `buruuj.ncr`, or `buruuj.snag`.

---

## Sequences

All document numbering uses `ir.sequence` records defined in `buruuj_base/data/ir_sequence_data.xml`:

```
TND/{year}/00001    Tender
PRJ/{year}/0001     Project Code
SC/{year}/00001     Subcontract
WO/{year}/00001     Work Order
CIPC/{year}/00001   Client IPC
SIPC/{year}/00001   Subcontractor IPC
DPR/{year}/{month}/0001  Daily Progress Report
RFI/{year}/00001    Request for Information
NCR/{year}/00001    Non-Conformance Report
VO/{year}/00001     Variation Order
INC/{year}/00001    HSE Incident
PTW/{year}/00001    Permit to Work
DWG/00001           Drawing Number
```

Adjust prefixes to match Buruuj's document numbering policy if needed.

---

## Conventions Used

* All custom models prefixed `buruuj.` to avoid namespace collision.
* Odoo 19 syntax throughout: `<list>` (not `<tree>`), `invisible="..."` (not `attrs`), `<chatter/>` shortcut, `_compute_display_name`.
* Monetary fields always paired with `currency_id`.
* All workflows use selection state fields with explicit action buttons.
* Tracked changes via `mail.thread` on important records.
* `@api.model_create_multi` on all `create` overrides.

---

## What's NOT Included (Recommended Extensions)

This codebase is the construction-specific spine. The following layer on top of standard Odoo Enterprise apps and would typically be configured in implementation, not built as custom addons:

* **Procurement, Inventory, Stores** — use Odoo `purchase` + `stock` with workflow rules.
* **HR & Payroll** — use Odoo `hr` + `hr_payroll` with localization.
* **Accounting & WIP** — use Odoo `account` with construction analytic accounts.
* **Mobile App** — use Odoo's responsive UI; native mobile is a separate workstream.
* **Portals** — extend Odoo's `portal` module with branded controllers.
* **BIM / Primavera integrations** — connector add-ons against this data model.

---

## File Layout

Each module follows the same structure:

```
buruuj_<module>/
├── __manifest__.py
├── __init__.py
├── models/
│   ├── __init__.py
│   └── *.py
├── views/
│   ├── *_views.xml
│   └── *_menus.xml
├── security/
│   ├── ir.model.access.csv
│   └── (buruuj_security.xml — base only)
├── data/
│   └── *.xml (sequences, master data — base only)
└── static/description/
```

---

## Version & License

* Odoo Series: **19.0**
* Module Version: **19.0.1.0.0**
* License: **OPL-1** (Odoo Proprietary License)
* Author: **Buruuj Construction Co.**

---

## Next Steps for Implementation Partner

1. **Discovery workshop**: confirm field requirements per role match Buruuj's actual workflow.
2. **Localization**: layer in country-specific tax (VAT, WHT), e-invoicing, and labor regulations.
3. **Data migration**: import master rates, subcontractors, drawing register from legacy.
4. **Reports**: design QWeb PDF layouts for IPC certificate, subcontract, work order, transmittal.
5. **Mobile**: configure Odoo's mobile app with site-engineer-friendly views; consider offline DPR capture.
6. **Portals**: enable subcontractor and client portals against the existing models.
7. **BI**: build CEO dashboard tiles in Odoo's dashboard module on top of `buruuj.dashboard` data.
