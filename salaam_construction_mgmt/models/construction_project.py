# -*- coding: utf-8 -*-
from datetime import timedelta
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError


class ConstructionProject(models.Model):
    """
    Master construction project record.
    Links:  dev.contract.istisna  →  salaam.construction.project
            salaam.construction.project  →  project.project (Odoo native)
    Tracks: phases, budget lines, site reports, drawing register,
            subcontractor tasks, governance documents.
    """
    _name = 'salaam.construction.project'
    _description = 'Construction Project'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'name'

    # ── IDENTITY ─────────────────────────────────────────────────────────────
    name = fields.Char(
        string='Project Name', required=True, tracking=True,
    )
    code = fields.Char(
        string='Project Code', copy=False,
        default=lambda self: _('New'),
    )
    state = fields.Selection([
        ('draft',        'Draft'),
        ('planning',     'Planning'),
        ('active',       'Active / Under Construction'),
        ('on_hold',      'On Hold'),
        ('handover',     'Handover'),
        ('completed',    'Completed'),
        ('cancelled',    'Cancelled'),
    ], string='Status', default='draft', required=True, tracking=True)

    company_id = fields.Many2one(
        'res.company', string='Branch', required=True,
        default=lambda self: self.env.company,
    )
    project_manager_id = fields.Many2one(
        'res.users', string='Project Manager', required=True,
        default=lambda self: self.env.user,
        tracking=True,
    )
    site_engineer_id = fields.Many2one(
        'res.users', string='Site Engineer', tracking=True,
    )

    # ── CONTRACT LINKS ────────────────────────────────────────────────────────
    istisna_contract_id = fields.Many2one(
        'dev.contract.istisna',
        string='Istisna Contract',
        ondelete='restrict',
        tracking=True,
        help='Primary Istisna (construction finance) contract funding this project',
    )
    property_id = fields.Many2one(
        'property.details', string='Property / Development',
        related='istisna_contract_id.property_id', store=True, readonly=True,
    )
    contractor_id = fields.Many2one(
        'res.partner', string='Main Contractor',
        related='istisna_contract_id.contractor_id', store=True, readonly=True,
    )

    # ── ODOO NATIVE PROJECT LINK ──────────────────────────────────────────────
    odoo_project_id = fields.Many2one(
        'project.project',
        string='Linked Odoo Project',
        ondelete='set null',
        help='Native Odoo project — auto-created when project is activated',
    )

    # ── LOCATION & CLASSIFICATION ─────────────────────────────────────────────
    location = fields.Char(string='Site Location')
    project_type = fields.Selection([
        ('residential',    'Residential'),
        ('commercial',     'Commercial'),
        ('mixed_use',      'Mixed Use'),
        ('infrastructure', 'Infrastructure'),
    ], string='Project Type', required=True, default='residential')
    total_built_area = fields.Float(string='Total Built Area (m²)', digits=(10, 2))
    num_units = fields.Integer(string='Number of Units')

    # ── DATES ─────────────────────────────────────────────────────────────────
    date_start_planned = fields.Date(
        string='Planned Start',
        related='istisna_contract_id.construction_start',
        store=True, readonly=True,
    )
    date_end_planned = fields.Date(
        string='Planned Completion',
        related='istisna_contract_id.expected_completion',
        store=True, readonly=True,
    )
    date_start_actual = fields.Date(string='Actual Start Date', tracking=True)
    date_end_actual = fields.Date(string='Actual Completion Date', tracking=True)

    # ── BUDGET ────────────────────────────────────────────────────────────────
    currency_id = fields.Many2one(
        'res.currency', string='Currency',
        default=lambda self: self.env.ref('base.USD'),
    )
    contract_value = fields.Monetary(
        string='Contract Value (Istisna)',
        related='istisna_contract_id.contract_value',
        currency_field='currency_id', store=True, readonly=True,
    )
    approved_budget = fields.Monetary(
        string='Approved Budget', currency_field='currency_id', tracking=True,
    )
    total_committed = fields.Monetary(
        string='Total Committed', compute='_compute_budget_totals',
        currency_field='currency_id', store=True,
    )
    total_spent = fields.Monetary(
        string='Total Spent', compute='_compute_budget_totals',
        currency_field='currency_id', store=True,
    )
    budget_variance = fields.Monetary(
        string='Budget Variance', compute='_compute_budget_totals',
        currency_field='currency_id', store=True,
    )
    budget_pct_spent = fields.Float(
        string='% Budget Spent', compute='_compute_budget_totals',
        digits=(5, 1), store=True,
    )

    # ── PROGRESS ──────────────────────────────────────────────────────────────
    overall_progress = fields.Float(
        string='Overall Progress (%)', digits=(5, 1),
        compute='_compute_overall_progress', store=True,
    )
    last_report_date = fields.Date(
        string='Last Site Report', compute='_compute_last_report', store=True,
    )

    # ── CHILD RECORDS ─────────────────────────────────────────────────────────
    phase_ids = fields.One2many(
        'salaam.construction.phase', 'project_id', string='Phases',
    )
    phase_count = fields.Integer(compute='_compute_counts', string='Phases')

    budget_line_ids = fields.One2many(
        'salaam.budget.line', 'project_id', string='Budget Lines',
    )
    budget_line_count = fields.Integer(compute='_compute_counts', string='Budget Lines')

    site_report_ids = fields.One2many(
        'salaam.site.report', 'project_id', string='Site Reports',
    )
    site_report_count = fields.Integer(compute='_compute_counts', string='Site Reports')

    drawing_ids = fields.One2many(
        'salaam.drawing.register', 'project_id', string='Drawing Register',
    )
    drawing_count = fields.Integer(compute='_compute_counts', string='Drawings')

    governance_doc_ids = fields.One2many(
        'salaam.governance.document', 'project_id', string='Governance Documents',
    )
    governance_doc_count = fields.Integer(compute='_compute_counts', string='Gov. Docs')

    subcontract_ids = fields.One2many(
        'dev.contract.subcontractor', 'parent_istisna_id',
        string='Sub-Contracts',
        related='istisna_contract_id.subcontract_ids',
    )
    subcontract_count = fields.Integer(compute='_compute_counts', string='Sub-Contracts')

    progress_snapshot_ids = fields.One2many(
        'salaam.construction.progress.snapshot', 'project_id',
        string='Progress Snapshots',
    )
    progress_snapshot_count = fields.Integer(
        compute='_compute_counts', string='Snapshots',
    )

    # ── EARNED-VALUE TOTALS (live, today) ─────────────────────────────────────
    planned_value_total = fields.Monetary(
        string='Planned Value (BCWS)',
        compute='_compute_earned_value_totals',
        currency_field='currency_id',
    )
    earned_value_total = fields.Monetary(
        string='Earned Value (BCWP)',
        compute='_compute_earned_value_totals',
        currency_field='currency_id',
    )
    actual_value_total = fields.Monetary(
        string='Actual Cost (ACWP)',
        compute='_compute_earned_value_totals',
        currency_field='currency_id',
    )
    spi_live = fields.Float(
        string='SPI (live)', digits=(5, 2),
        compute='_compute_earned_value_totals',
    )
    cpi_live = fields.Float(
        string='CPI (live)', digits=(5, 2),
        compute='_compute_earned_value_totals',
    )

    # ── COMPUTED ──────────────────────────────────────────────────────────────
    @api.depends(
        'budget_line_ids.committed_amount',
        'budget_line_ids.spent_amount',
        'approved_budget',
    )
    def _compute_budget_totals(self):
        for rec in self:
            committed = sum(rec.budget_line_ids.mapped('committed_amount'))
            spent = sum(rec.budget_line_ids.mapped('spent_amount'))
            budget = rec.approved_budget or 0
            rec.total_committed = committed
            rec.total_spent = spent
            rec.budget_variance = budget - spent
            rec.budget_pct_spent = (spent / budget * 100) if budget else 0

    @api.depends('phase_ids.progress', 'phase_ids.weight')
    def _compute_overall_progress(self):
        for rec in self:
            phases = rec.phase_ids
            if not phases:
                rec.overall_progress = 0
                continue
            total_weight = sum(phases.mapped('weight')) or 1
            weighted = sum(p.progress * p.weight for p in phases)
            rec.overall_progress = weighted / total_weight

    @api.depends('site_report_ids.report_date')
    def _compute_last_report(self):
        for rec in self:
            reports = rec.site_report_ids.sorted('report_date', reverse=True)
            rec.last_report_date = reports[0].report_date if reports else False

    @api.depends(
        'phase_ids', 'budget_line_ids', 'site_report_ids',
        'drawing_ids', 'governance_doc_ids',
        'istisna_contract_id.subcontract_ids',
        'progress_snapshot_ids',
    )
    def _compute_counts(self):
        for rec in self:
            rec.phase_count = len(rec.phase_ids)
            rec.budget_line_count = len(rec.budget_line_ids)
            rec.site_report_count = len(rec.site_report_ids)
            rec.drawing_count = len(rec.drawing_ids)
            rec.governance_doc_count = len(rec.governance_doc_ids)
            rec.subcontract_count = len(rec.subcontract_ids)
            rec.progress_snapshot_count = len(rec.progress_snapshot_ids)

    @api.depends(
        'phase_ids.planned_value',
        'phase_ids.earned_value',
        'phase_ids.actual_value',
    )
    def _compute_earned_value_totals(self):
        for rec in self:
            pv = sum(rec.phase_ids.mapped('planned_value'))
            ev = sum(rec.phase_ids.mapped('earned_value'))
            ac = sum(rec.phase_ids.mapped('actual_value'))
            rec.planned_value_total = pv
            rec.earned_value_total = ev
            rec.actual_value_total = ac
            rec.spi_live = (ev / pv) if pv else 0.0
            rec.cpi_live = (ev / ac) if ac else 0.0

    # ── ORM ───────────────────────────────────────────────────────────────────
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('code', _('New')) == _('New'):
                vals['code'] = self.env['ir.sequence'].next_by_code(
                    'salaam.construction.project'
                ) or _('New')
        return super().create(vals_list)

    # ── WORKFLOW ──────────────────────────────────────────────────────────────
    def action_start_planning(self):
        self.write({'state': 'planning'})

    def action_activate(self):
        """Activate project — auto-create native Odoo project if not exists."""
        for rec in self:
            if not rec.odoo_project_id:
                odoo_proj = self.env['project.project'].create({
                    'name': rec.name,
                    'user_id': rec.project_manager_id.id,
                    'company_id': rec.company_id.id,
                    'description': _(
                        'Auto-created from Salaam Construction Project %s'
                    ) % rec.code,
                })
                rec.odoo_project_id = odoo_proj
            if not rec.date_start_actual:
                rec.date_start_actual = fields.Date.today()
            rec.state = 'active'
            rec.message_post(
                body=_('Project activated. Odoo project %s linked.')
                % (rec.odoo_project_id.name if rec.odoo_project_id else '')
            )

    def action_put_on_hold(self):
        self.write({'state': 'on_hold'})

    def action_handover(self):
        self.write({'state': 'handover'})

    def action_complete(self):
        for rec in self:
            if not rec.date_end_actual:
                rec.date_end_actual = fields.Date.today()
            # Update linked Istisna contract
            if rec.istisna_contract_id and rec.istisna_contract_id.state == 'active':
                rec.istisna_contract_id.action_complete()
        self.write({'state': 'completed'})

    def action_cancel(self):
        self.write({'state': 'cancelled'})

    # ── SMART BUTTON ACTIONS ──────────────────────────────────────────────────
    def action_open_phases(self):
        self.ensure_one()
        return self._open_related('salaam.construction.phase', 'project_id', 'Phases')

    def action_open_budget(self):
        self.ensure_one()
        return self._open_related('salaam.budget.line', 'project_id', 'Budget')

    def action_open_site_reports(self):
        self.ensure_one()
        return self._open_related('salaam.site.report', 'project_id', 'Site Reports')

    def action_open_drawings(self):
        self.ensure_one()
        return self._open_related('salaam.drawing.register', 'project_id', 'Drawing Register')

    def action_open_governance_docs(self):
        self.ensure_one()
        return self._open_related('salaam.governance.document', 'project_id', 'Governance Documents')

    def action_open_odoo_project(self):
        self.ensure_one()
        if not self.odoo_project_id:
            raise UserError(_('No Odoo Project linked yet. Activate the project first.'))
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'project.project',
            'res_id': self.odoo_project_id.id,
            'view_mode': 'form',
        }

    def _open_related(self, model, field, name):
        return {
            'type': 'ir.actions.act_window',
            'name': _(name),
            'res_model': model,
            'view_mode': 'list,form',
            'domain': [(field, '=', self.id)],
            'context': {'default_%s' % field: self.id},
        }

    # ── GANTT & S-CURVE ───────────────────────────────────────────────────────
    def action_open_gantt(self):
        """Open the task Gantt chart filtered to this project."""
        self.ensure_one()
        action = self.env['ir.actions.act_window']._for_xml_id(
            'salaam_construction_mgmt.action_construction_task_gantt'
        )
        action['domain'] = [('project_id', '=', self.id)]
        action['context'] = {
            'default_project_id': self.id,
            'search_default_project_id': self.id,
        }
        return action

    def action_open_scurve(self):
        """Open the S-curve graph view for this project."""
        self.ensure_one()
        if not self.progress_snapshot_ids:
            self.action_generate_snapshots()
        return {
            'type': 'ir.actions.act_window',
            'name': _('S-Curve — %s') % self.name,
            'res_model': 'salaam.construction.progress.snapshot',
            'view_mode': 'graph,pivot,list',
            'domain': [('project_id', '=', self.id)],
            'context': {'default_project_id': self.id},
        }

    def action_generate_snapshots(self):
        """
        (Re-)generate weekly progress snapshots between project start and
        max(today, planned end). Snapshots are derived data; the existing rows
        for each project are dropped and rebuilt from current task/phase state.

        Planned curve   — cumulative PV across all tasks at each snapshot date.
        Earned curve    — for past dates uses recorded progress today
                          (no progress history is captured per snapshot),
                          producing a single live point-in-time earned line.
                          The historical earned/actual columns are approximated
                          by interpolating today's totals back along the elapsed
                          schedule — good enough for the visual S-curve while
                          progress history isn't stored separately.
        """
        Snapshot = self.env['salaam.construction.progress.snapshot']
        for project in self:
            start = project.date_start_actual or project.date_start_planned
            end = project.date_end_planned
            if not start or not end:
                raise UserError(_(
                    'Set a planned start and planned end on the project '
                    '(or on its Istisna contract) before generating snapshots.'
                ))
            today = fields.Date.context_today(self)
            horizon = max(end, today)

            Snapshot.search([('project_id', '=', project.id)]).unlink()

            tasks = project.phase_ids.mapped('task_ids').filtered(
                lambda t: t.date_start_planned and t.date_end_planned
                and t.budget_cost
            )
            total_budget = sum(tasks.mapped('budget_cost')) or 0.0
            ev_today = project.earned_value_total or 0.0
            ac_today = project.actual_value_total or 0.0

            rows = []
            cur = start
            step = timedelta(days=7)
            while cur <= horizon:
                # Planned cumulative cost at cur — linear interp per task
                planned_cum = 0.0
                for t in tasks:
                    if cur <= t.date_start_planned:
                        pct = 0.0
                    elif cur >= t.date_end_planned:
                        pct = 1.0
                    else:
                        total_days = (
                            t.date_end_planned - t.date_start_planned
                        ).days or 1
                        pct = (cur - t.date_start_planned).days / total_days
                    planned_cum += (t.budget_cost or 0.0) * pct
                planned_pct = (
                    planned_cum / total_budget * 100.0
                ) if total_budget else 0.0

                # Earned/actual — interp today's totals back along the schedule
                # so the curves render as a trend even without history.
                if cur >= today:
                    ev = ev_today
                    ac = ac_today
                else:
                    span = (today - start).days or 1
                    ratio = max(0.0, min(1.0, (cur - start).days / span))
                    ev = ev_today * ratio
                    ac = ac_today * ratio
                actual_pct = (
                    ev / total_budget * 100.0
                ) if total_budget else 0.0

                rows.append({
                    'project_id': project.id,
                    'snapshot_date': cur,
                    'planned_pct_cumulative': planned_pct,
                    'actual_pct_cumulative': actual_pct,
                    'planned_cost_cumulative': planned_cum,
                    'earned_value_cumulative': ev,
                    'actual_cost_cumulative': ac,
                })
                cur += step
            if rows:
                Snapshot.create(rows)
            project.message_post(body=_(
                '%d progress snapshots regenerated.'
            ) % len(rows))
        return True

    def action_open_progress_snapshots(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Progress Snapshots'),
            'res_model': 'salaam.construction.progress.snapshot',
            'view_mode': 'list,graph,pivot,form',
            'domain': [('project_id', '=', self.id)],
            'context': {'default_project_id': self.id},
        }
