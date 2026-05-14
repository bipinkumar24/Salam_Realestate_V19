# -*- coding: utf-8 -*-
{
    'name': 'Buruuj Construction - Site Operations',
    'version': '19.0.1.0.0',
    'category': 'Construction',
    'summary': 'Daily progress reports, RFIs, NCRs, snag list, ITPs — mobile-first',
    'description': """
Site Operations (Mobile-First)
================================
* Daily Progress Report (DPR) with weather, manpower, equipment
* Request for Information (RFI) with consultant turnaround tracking
* Non-Conformance Report (NCR) with corrective action workflow
* Snag list / punch list with photo evidence
* Inspection Test Plans (ITP) with digital sign-off
""",
    'author': 'Buruuj Construction Co.',
    'license': 'OPL-1',
    'depends': ['buruuj_base', 'buruuj_project', 'mail'],
    'data': [
        'security/ir.model.access.csv',
        'views/buruuj_dpr_views.xml',
        'views/buruuj_rfi_views.xml',
        'views/buruuj_ncr_views.xml',
        'views/buruuj_snag_views.xml',
        'views/buruuj_itp_views.xml',
        'views/buruuj_site_menus.xml',
    ],
    'installable': True,
    'application': False,
}
