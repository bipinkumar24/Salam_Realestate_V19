# -*- coding: utf-8 -*-
{
    'name': 'Salaam HSE — Health, Safety & Environment Register',
    'version': '19.0.1.0.0',
    'summary': 'HSE incidents, method statements, toolbox talks, audits — Djibouti site compliance',
    'description': """
salaam_hse
==========
Lightweight HSE management extension for buruuj_project.
Covers Djibouti regulatory requirements and Islamic finance ESG obligations.

Models:
-------
1. salaam.hse.incident
   Site incident log: near-miss, first-aid, lost-time, dangerous-occurrence, fatality.
   RIDDOR-equivalent classification for Djibouti. Immediate notification chain.
   Status: reported -> investigating -> closed / escalated
   Links to phase, contractor, and location on site.

2. salaam.hse.method.statement
   Method statement (RAMS) register per work activity.
   Status: draft -> submitted -> approved / rejected
   Approval required before work commences.
   Links to construction phase and contractor.

3. salaam.hse.toolbox.talk
   Toolbox talk record. Date, topic, attendees, conductor.
   Frequency tracking — weekly target per site.
   Links to project and contractor party.

4. salaam.hse.audit
   Periodic HSE audit record.
   Internal / External / Regulatory audit types.
   Findings with severity classification.
   Status: planned -> conducted -> findings_issued -> closed
   Corrective action items tracked.
""",
    'author': 'Salaam Investment Bank — IAFAO',
    'category': 'Construction',
    'license': 'LGPL-3',
    'depends': [
        'base', 'mail',
        'buruuj_project',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/sequences.xml',
        'data/hse_seed.xml',
        'views/incident_views.xml',
        'views/method_statement_views.xml',
        'views/toolbox_talk_views.xml',
        'views/hse_audit_views.xml',
        'views/project_inherit_views.xml',
        'views/menus.xml',
        'report/hse_dashboard_report.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
