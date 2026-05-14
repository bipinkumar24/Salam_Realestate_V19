# -*- coding: utf-8 -*-
from odoo import models, fields, api


class BuruujDashboard(models.TransientModel):
    """Aggregated KPI dashboard for executives.

    Lightweight transient model — values are computed on the fly from
    underlying models so the dashboard always reflects current data."""
    _name = 'buruuj.dashboard'
    _description = 'Executive Dashboard'

    name = fields.Char(default='Construction Portfolio Dashboard')

    # Project KPIs
    active_projects = fields.Integer(compute='_compute_kpis')
    projects_green = fields.Integer(compute='_compute_kpis')
    projects_amber = fields.Integer(compute='_compute_kpis')
    projects_red = fields.Integer(compute='_compute_kpis')

    # Financial KPIs
    total_contract_value = fields.Monetary(compute='_compute_kpis')
    total_baseline_budget = fields.Monetary(compute='_compute_kpis')
    total_revised_budget = fields.Monetary(compute='_compute_kpis')

    # Tender pipeline
    open_tenders = fields.Integer(compute='_compute_kpis')
    pipeline_value = fields.Monetary(compute='_compute_kpis')
    won_ytd = fields.Integer(compute='_compute_kpis')
    lost_ytd = fields.Integer(compute='_compute_kpis')
    win_rate = fields.Float(compute='_compute_kpis')

    # Subcontractor exposure
    active_subcontracts = fields.Integer(compute='_compute_kpis')
    subcontract_exposure = fields.Monetary(compute='_compute_kpis')

    # IPC pipeline
    pending_client_ipcs = fields.Integer(compute='_compute_kpis')
    pending_sub_ipcs = fields.Integer(compute='_compute_kpis')
    payable_to_subs = fields.Monetary(compute='_compute_kpis')
    receivable_from_clients = fields.Monetary(compute='_compute_kpis')

    # Top risks
    high_risk_count = fields.Integer(compute='_compute_kpis')

    currency_id = fields.Many2one(
        'res.currency', default=lambda s: s.env.company.currency_id)

    @api.depends_context('uid')
    def _compute_kpis(self):
        from datetime import date
        Project = self.env['project.project']
        Tender = self.env['buruuj.tender']
        Sub = self.env['buruuj.subcontract']
        IPC = self.env['buruuj.ipc']
        Risk = self.env['buruuj.risk']
        year_start = date(date.today().year, 1, 1)

        for rec in self:
            projects = Project.search(
                [('buruuj_project_code', '!=', False),
                 ('active', '=', True)])
            rec.active_projects = len(projects)
            rec.projects_green = len(projects.filtered(
                lambda p: p.buruuj_health == 'green'))
            rec.projects_amber = len(projects.filtered(
                lambda p: p.buruuj_health == 'amber'))
            rec.projects_red = len(projects.filtered(
                lambda p: p.buruuj_health == 'red'))
            rec.total_contract_value = sum(projects.mapped('buruuj_contract_value'))
            rec.total_baseline_budget = sum(projects.mapped('buruuj_baseline_budget'))
            rec.total_revised_budget = sum(projects.mapped('buruuj_revised_budget'))

            open_tenders = Tender.search(
                [('state', 'in', ['estimating', 'reviewing', 'submitted'])])
            rec.open_tenders = len(open_tenders)
            rec.pipeline_value = sum(open_tenders.mapped('bid_value'))
            rec.won_ytd = Tender.search_count(
                [('state', '=', 'won'), ('create_date', '>=', year_start)])
            rec.lost_ytd = Tender.search_count(
                [('state', '=', 'lost'), ('create_date', '>=', year_start)])
            decided = rec.won_ytd + rec.lost_ytd
            rec.win_rate = (100.0 * rec.won_ytd / decided) if decided else 0.0

            active_subs = Sub.search(
                [('state', 'in', ['signed', 'in_progress'])])
            rec.active_subcontracts = len(active_subs)
            rec.subcontract_exposure = sum(active_subs.mapped('contract_value'))

            rec.pending_client_ipcs = IPC.search_count([
                ('type', '=', 'client'),
                ('state', 'in', ['draft', 'qs_approved', 'pm_approved'])])
            rec.pending_sub_ipcs = IPC.search_count([
                ('type', '=', 'subcontractor'),
                ('state', 'in', ['draft', 'qs_approved', 'pm_approved'])])
            rec.payable_to_subs = sum(IPC.search([
                ('type', '=', 'subcontractor'),
                ('state', '=', 'finance_approved')]).mapped('total_payable'))
            rec.receivable_from_clients = sum(IPC.search([
                ('type', '=', 'client'),
                ('state', '=', 'finance_approved')]).mapped('total_payable'))

            rec.high_risk_count = Risk.search_count([
                ('state', '=', 'open'), ('severity', '>=', 12)])
