{
    'name': 'AI BOQ Reader',
    'version': '19.0.1.0.0',
    'category': 'Construction',
    'summary': 'AI-powered design layout reader that prepares Bill of Quantities templates',
    'description': """
AI BOQ Reader
=============
Upload architectural or engineering design layouts (PDF / PNG / JPG) and
automatically extract a Bill of Quantities (BOQ) using a vision-capable LLM
(Anthropic Claude or OpenAI GPT-4o).

Features
--------
* Drag-and-drop drawing upload (single file or batch wizard)
* Multi-page PDF support (auto rasterised to images)
* Pluggable AI provider (Anthropic / OpenAI / Azure OpenAI)
* Structured JSON extraction with confidence scores per line
* Editable BOQ lines with category grouping (civil, MEP, finishes, ...)
* QWeb PDF report with letterhead
* Optional Sales Order / Purchase Order generation
* Reusable BOQ templates
* **Pricelist cross-check** — re-prices AI lines against an Odoo pricelist,
  with fuzzy product matching by description for unmapped lines
* **Async analysis** — when OCA's queue_job is installed, the AI call is
  dispatched to a worker so the UI returns immediately
""",
    'author': 'Your Company',
    'website': 'https://example.com',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'mail',
        'product',
        'account',
        'project',
        'sale_management',  # for product.pricelist usage and sale.order creation
    ],
    # Optional: install OCA queue_job to enable async AI analysis (toggle in Settings).
    'data': [
        'security/boq_security.xml',
        'security/ir.model.access.csv',
        'views/boq_template_views.xml',
        'views/boq_project_views.xml',
        'views/res_config_settings_views.xml',
        'wizards/boq_import_wizard_views.xml',
        'reports/boq_report.xml',
        'reports/boq_report_templates.xml',
        'views/menus.xml',
    ],
    'demo': [
        'data/boq_demo.xml',
    ],
    'external_dependencies': {
        # pdf2image is only required if you use OpenAI/Azure for PDFs, or set
        # ai_boq.force_rasterize=True. Anthropic supports PDFs natively.
        'python': ['anthropic', 'Pillow'],
    },
    'installable': True,
    'application': True,
    'auto_install': False,
}
