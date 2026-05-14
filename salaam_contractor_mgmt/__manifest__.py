# -*- coding: utf-8 -*-
{
    'name': 'Salaam Contractor Management',
    'version': '19.0.1.0.0',
    'summary': 'Site Instructions, NCRs, EOT Claims, Contractor Programme — PM to Contractor interface',
    'description': """
salaam_contractor_mgmt
======================
Fills the gap between the Project Manager and the Contractor
during construction execution.

Models:
-------
1. salaam.site.instruction (SI-YYYY-NNNN)
   Engineer's / PM's formal written instructions to the contractor.
   Covers: scope changes, design clarifications, urgent directions,
   daywork authorisations, material substitutions.
   Status: draft -> issued -> acknowledged -> completed / disputed
   Links to: IPC (if variation cost), EOT (if time impact),
             phase, construction project, contractor party.
   Every change to the works must be backed by an SI.

2. salaam.ncr (NCR-YYYY-NNNN)
   Non-Conformance Report — quality failure during construction.
   Raised by QA Engineer, PM, or Independent Certifier.
   Contractor must submit Corrective Action Plan (CAP).
   Status: open -> cap_submitted -> cap_approved -> rectifying -> closed / rejected
   Severity: critical (stop work) / major / minor / observation
   Links to: phase, drawing, snag list (if carried to handover).
   Distinct from snagging — NCRs happen DURING construction.

3. salaam.eot.claim (EOT-YYYY-NNNN)
   Extension of Time claim by contractor.
   Events: employer delay, force majeure, adverse weather,
           late instructions, variations, utility strikes.
   Status: submitted -> under_assessment -> granted / rejected / partial
   Links to: site instruction (cause), programme,
             original completion date, revised completion date.
   Tracks: days claimed, days granted, running EOT total.

4. salaam.contractor.programme (PROG-YYYY-NNNN)
   Contractor programme submission and approval register.
   Programme types: baseline, revised, recovery, as-built.
   Status: draft -> submitted -> under_review -> approved / rejected
   Key dates: programme start, programme end, float, critical path flag.
   Links to: construction phases (maps programme to platform phases).
   Revision history tracked — every approved revision supersedes prior.
""",
    'author': 'Salaam Investment Bank — IAFAO',
    'category': 'Construction',
    'license': 'LGPL-3',
    'depends': [
        'base', 'mail',
        'salaam_construction_mgmt',
        'salaam_dev_contracts',
        'salaam_procurement','salaam_handover',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/sequences.xml',
        'views/site_instruction_views.xml',
        'views/ncr_views.xml',
        'views/eot_claim_views.xml',
        'views/contractor_programme_views.xml',
        'views/project_inherit_views.xml',
        'views/menus.xml',
        'report/si_report.xml',
        'report/ncr_report.xml',
        'report/eot_report.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
