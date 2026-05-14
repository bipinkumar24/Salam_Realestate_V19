# -*- coding: utf-8 -*-
{
    'name': 'Cash Purchase & Payment Plans — BRE Platform',
    'version': '19.0.1.0.1',
    'summary': 'Cash purchase mode with auto-generated payment plans on the BRE financing platform.',
    'description': """
Cash Purchase & Payment Plans
==============================
Adds a Purchase Mode selector to every BRE financing application.

When "Cash Purchase" is selected:
  ✅ Financing fields (type, amount, tenure) are hidden automatically
  ✅ Five Cs appraisal button is blocked with a clear message
  ✅ Payment plan type selector appears (Full / Instalment / Construction / Custom)
  ✅ "Create Payment Plan" button generates a full instalment schedule
  ✅ Real estate agent is notified via application chatter
  ✅ Payment schedule is visible to the client on the portal

Four plan types:
  1. Full Payment Upfront  — 100% on booking
  2. Instalment Plan       — configurable split (default: 30/40/30)
  3. Construction-Linked   — 5 milestone payments over build period
  4. Custom Split          — officer defines each line manually

Features:
  - Plan templates with reusable instalment structures
  - Per-line "Mark Paid" button with date and receipt reference
  - Completion % progress tracking
  - Next due date and amount surfaced on application
  - Overdue / Due / Pending status with colour coding
  - Portal page for client to view their payment schedule
  - Full chatter history on plan and application
    """,
    'author': 'Salaam Investment Bank — IAFAO',
    'category': 'Banking / Real Estate',
    'license': 'LGPL-3',
    'depends': [
        'bank_realestate_collab',
        'portal',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/payment_plan_templates.xml',
        'views/cash_purchase_views.xml',
    ],
    'external_dependencies': {
        'python': ['dateutil'],
    },
    'pre_init_hook': 'pre_init_hook',
    'installable': True,
    'auto_install': False,
    'application': False,
}
