# -*- coding: utf-8 -*-
{
    'name': 'Pre-Tender Management',
    'version': '19.0.1.1.0',
    'category': 'Sales/CRM',
    'summary': 'Full pre-tender lifecycle: qualification, compliance, survey, capture, risk, kickoff',
    'description': """
Pre-Tender Management — Full Checklist Coverage
================================================
End-to-end pre-tender lifecycle aligned with the three-tier importance model.

TIER 1 — CRITICAL
* Opportunity qualification (eligibility, Pwin, incumbent, wired-tender flag)
* Compliance matrix and mandatory certificate registry with expiry alerts
* Bid bond / EMD tracker
* Site survey planning, mobile findings capture, BoQ discrepancy flagging
* Bid / No-Bid scoring matrix, cost-of-bid calculator, approval workflow

TIER 2 — HIGH IMPORTANCE
* Capture plan with milestones, win themes, discriminators, ghost strategy
* Risk register with probability x impact heatmap and reserve tracking
* Bid team allocation from HR with key-personnel flag
* Subcontractor / JV / NDA partner agreement registry
* 3-quote supplier budgetary quote tracker
* Stakeholder map (decision-maker, influencer, evaluator, gatekeeper)
* Pre-bid meeting register and clarification Q&A log

TIER 3 — SUPPORTING
* Competitor master records with strengths, weaknesses, past awards
* SWOT generator per opportunity / competitor
* Pink / Red / Gold review gates with action items
* Multi-source lead alert subscriptions (TED, UNGM, government portals)

Workflow gates enforce Tier 1 completion before Won status.
""",
    'author': 'Buruuj',
    'license': 'LGPL-3',
    'depends': [
        'crm',
        'mail',
        'hr',
        'account',
        'approvals',
        'documents',
        'calendar',
    ],
    'data': [
        'security/tender_security.xml',
        'security/ir.model.access.csv',
        'data/tender_sequences.xml',
        'views/tender_compliance_certificate_views.xml',
        'views/tender_compliance_matrix_views.xml',
        'views/tender_bid_decision_views.xml',
        'views/tender_bid_bond_views.xml',
        'views/tender_site_survey_views.xml',
        'views/tender_capture_plan_views.xml',
        'views/tender_risk_views.xml',
        'views/tender_partner_agreement_views.xml',
        'views/tender_budget_quote_views.xml',
        'views/tender_stakeholder_views.xml',
        'views/tender_clarification_views.xml',
        'views/tender_prebid_meeting_views.xml',
        'views/tender_bid_team_views.xml',
        'views/tender_competitor_views.xml',
        'views/tender_kickoff_gate_views.xml',
        'views/tender_alert_subscription_views.xml',
        'views/hr_employee_views.xml',
        'views/tender_opportunity_views.xml',
        'views/res_partner_views.xml',
        'views/tender_menus.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}
