# -*- coding: utf-8 -*-
{
    'name': 'Buruuj Construction - AI Assistant',
    'version': '19.0.1.0.0',
    'category': 'Construction',
    'summary': 'AI-powered drafting: BOQ from drawings, NCR from photos, subcontractor recommendations',
    'description': """
Buruuj AI Assistant
====================
Adds AI drafting capabilities to the Buruuj suite via the Anthropic Claude API.

Features:
* **BOQ Drafting from Drawings**: Upload tender drawings/specs (PDF), AI generates
  a draft BOQ with sections, items, quantities, and rate suggestions matched to
  the master rate database.
* **NCR Drafting from Photos**: On site, take a photo of a defect; AI drafts
  the description, root cause, and corrective action.
* **Subcontractor Recommendation**: AI ranks subcontractors for a given trade and
  project size based on scorecard history, current workload, and license validity.
* **Variation Order Drafting**: Given a client change request, AI drafts the VO
  with cost/time impact estimates.

Architecture:
* Async tasks via Odoo's job queue (buruuj.ai.task model)
* Configurable model selection (default: claude-opus-4-7)
* Token usage tracking per call for cost monitoring
* All AI suggestions are DRAFTS — final approval is always human

CRITICAL: AI is NEVER used for IPC calculations, financial approvals, contract
interpretation, or safety decisions. These remain deterministic and human-controlled.
""",
    'author': 'Buruuj Construction Co.',
    'license': 'OPL-1',
    'depends': [
        'buruuj_base', 'buruuj_tendering', 'buruuj_project',
        'buruuj_subcontractor', 'buruuj_site_ops',
    ],
    # Note: 'project' module from Odoo core is pulled in transitively via buruuj_project
    'external_dependencies': {
        'python': ['anthropic'],
    },
    'data': [
        'security/ir.model.access.csv',
        'data/ir_config_parameter_data.xml',
        'data/ir_cron_data.xml',
        'views/res_config_settings_views.xml',
        'views/buruuj_ai_task_views.xml',
        'views/buruuj_ai_menus.xml',
        'views/buruuj_portfolio_digest_views.xml',
        'views/buruuj_boq_views.xml',
        'views/buruuj_ncr_views.xml',
        'views/buruuj_subcontract_views.xml',
        'views/buruuj_variation_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
