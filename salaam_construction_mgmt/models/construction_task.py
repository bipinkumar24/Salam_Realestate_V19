# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class ConstructionTask(models.Model):
    """
    Granular task within a construction phase.
    Links directly to a Subcontractor Agreement and/or native Odoo project.task.
    Tracks scope, responsible party, cost, and completion status.
    """
    _name = 'salaam.construction.task'
    _description = 'Construction Task'
    _order = 'sequence, id'
    _inherit = ['mail.thread']

    name = fields.Char(string='Task', required=True)
    sequence = fields.Integer(default=10)
    project_id = fields.Many2one(
        'salaam.construction.project', string='Project',
        required=True, ondelete='cascade', index=True,
    )
    phase_id = fields.Many2one(
        'salaam.construction.phase', string='Phase',
        required=True, ondelete='cascade', index=True,
    )
    istisna_contract_id = fields.Many2one(
        related='project_id.istisna_contract_id',
        store=True,
        readonly=True,
    )
    state = fields.Selection([
        ('todo',        'To Do'),
        ('in_progress', 'In Progress'),
        ('blocked',     'Blocked'),
        ('done',        'Done'),
        ('invoiced',    'Invoiced'),
        ('cancelled',   'Cancelled'),
    ], string='Status', default='todo', tracking=True)

    # ── RESPONSIBILITY ────────────────────────────────────────────────────────
    task_type = fields.Selection([
        ('main_contractor',  'Main Contractor'),
        ('subcontractor',    'Subcontractor'),
        ('bank_inspection',  'Bank / Inspection'),
        ('design',           'Design / Engineering'),
        ('admin',            'Administrative'),
    ], string='Task Type', required=True, default='main_contractor')

    assigned_to_id = fields.Many2one(
        'res.partner', string='Assigned To (Company / Individual)',
    )
    responsible_id = fields.Many2one(
        'res.users', string='Internal Responsible',
    )

    # ── SUBCONTRACT LINK ──────────────────────────────────────────────────────
    subcontract_id = fields.Many2one(
        'dev.contract.subcontractor',
        string='Subcontract Agreement',
        domain="[('parent_istisna_id','=',istisna_contract_id)]",
        tracking=True,
        help='Subcontractor agreement this task falls under',
    )
    subcontract_milestone_id = fields.Many2one(
        'dev.contract.milestone',
        string='Subcontract Milestone',
        domain="[('res_model','=','dev.contract.subcontractor')]",
        help='Payment milestone on the subcontract triggered by this task',
    )

    # ── ODOO NATIVE TASK LINK ─────────────────────────────────────────────────
    odoo_task_id = fields.Many2one(
        'project.task', string='Odoo Project Task',
        ondelete='set null',
        help='Synced native Odoo task for resource planning',
    )

    # ── SCOPE & DATES ─────────────────────────────────────────────────────────
    description = fields.Html(string='Task Description / Scope')
    date_start_planned = fields.Date(string='Planned Start')
    date_end_planned = fields.Date(string='Planned End')
    date_start_actual = fields.Date(string='Actual Start')
    date_end_actual = fields.Date(string='Actual End')
    progress = fields.Float(string='Progress (%)', digits=(5, 1))
    planned_duration_days = fields.Integer(
        string='Planned Duration (days)',
        compute='_compute_planned_duration', store=True,
    )

    # ── GANTT DEPENDENCY ──────────────────────────────────────────────────────
    predecessor_ids = fields.Many2many(
        'salaam.construction.task',
        'construction_task_dep_rel',
        'task_id', 'predecessor_id',
        string='Predecessor Tasks',
        domain="[('project_id','=',project_id),('id','!=',id)]",
        help='Tasks that must finish before this task can start (Finish-to-Start).',
    )
    successor_ids = fields.Many2many(
        'salaam.construction.task',
        'construction_task_dep_rel',
        'predecessor_id', 'task_id',
        string='Successor Tasks',
    )

    # ── COST ──────────────────────────────────────────────────────────────────
    currency_id = fields.Many2one(
        related='project_id.currency_id', store=True,
    )
    budget_cost = fields.Monetary(
        string='Budgeted Cost', currency_field='currency_id',
    )
    actual_cost = fields.Monetary(
        string='Actual Cost', currency_field='currency_id',
    )
    cost_variance = fields.Monetary(
        string='Cost Variance', compute='_compute_cost_variance',
        currency_field='currency_id', store=True,
    )
    invoice_id = fields.Many2one(
        'account.move', string='Invoice / Bill', ondelete='set null',
    )

    # ── EARNED-VALUE FIELDS (S-curve inputs) ──────────────────────────────────
    planned_pct_to_date = fields.Float(
        string='Planned % to Date',
        compute='_compute_earned_value', digits=(5, 1), store=False,
        help='Linear-interp planned completion percent based on today vs planned dates.',
    )
    planned_value = fields.Monetary(
        string='Planned Value (BCWS)',
        compute='_compute_earned_value',
        currency_field='currency_id', store=False,
        help='Budgeted Cost of Work Scheduled — budget × planned % to date.',
    )
    earned_value = fields.Monetary(
        string='Earned Value (BCWP)',
        compute='_compute_earned_value',
        currency_field='currency_id', store=False,
        help='Budgeted Cost of Work Performed — budget × actual progress %.',
    )
    schedule_variance = fields.Monetary(
        string='Schedule Variance (EV − PV)',
        compute='_compute_earned_value',
        currency_field='currency_id', store=False,
    )
    cost_performance_index = fields.Float(
        string='CPI',
        compute='_compute_earned_value', digits=(5, 2), store=False,
    )
    schedule_performance_index = fields.Float(
        string='SPI',
        compute='_compute_earned_value', digits=(5, 2), store=False,
    )

    # ── COMPUTED ──────────────────────────────────────────────────────────────
    @api.depends('budget_cost', 'actual_cost')
    def _compute_cost_variance(self):
        for rec in self:
            rec.cost_variance = rec.budget_cost - rec.actual_cost

    @api.depends('date_start_planned', 'date_end_planned')
    def _compute_planned_duration(self):
        for rec in self:
            if rec.date_start_planned and rec.date_end_planned:
                rec.planned_duration_days = (
                    rec.date_end_planned - rec.date_start_planned
                ).days + 1
            else:
                rec.planned_duration_days = 0

    @api.depends(
        'budget_cost', 'actual_cost', 'progress',
        'date_start_planned', 'date_end_planned',
    )
    def _compute_earned_value(self):
        today = fields.Date.context_today(self)
        for rec in self:
            budget = rec.budget_cost or 0.0
            # Planned % to date — linear between planned start/end
            if rec.date_start_planned and rec.date_end_planned:
                if today <= rec.date_start_planned:
                    planned_pct = 0.0
                elif today >= rec.date_end_planned:
                    planned_pct = 100.0
                else:
                    total = (rec.date_end_planned - rec.date_start_planned).days or 1
                    elapsed = (today - rec.date_start_planned).days
                    planned_pct = max(0.0, min(100.0, (elapsed / total) * 100.0))
            else:
                planned_pct = 0.0
            rec.planned_pct_to_date = planned_pct
            rec.planned_value = budget * planned_pct / 100.0
            rec.earned_value = budget * (rec.progress or 0.0) / 100.0
            rec.schedule_variance = rec.earned_value - rec.planned_value
            rec.cost_performance_index = (
                rec.earned_value / rec.actual_cost
            ) if rec.actual_cost else 0.0
            rec.schedule_performance_index = (
                rec.earned_value / rec.planned_value
            ) if rec.planned_value else 0.0

    # ── ACTIONS ───────────────────────────────────────────────────────────────
    def action_start(self):
        self.write({'state': 'in_progress',
                    'date_start_actual': fields.Date.today()})
        self._sync_to_odoo_task()

    def action_done(self):
        self.write({'state': 'done', 'progress': 100.0,
                    'date_end_actual': fields.Date.today()})
        # Trigger subcontract milestone completion if linked
        if self.subcontract_milestone_id:
            self.subcontract_milestone_id.action_mark_completed()
        self._sync_to_odoo_task()

    def action_block(self):
        self.write({'state': 'blocked'})

    def action_invoice(self):
        self.write({'state': 'invoiced'})
        if self.subcontract_milestone_id:
            self.subcontract_milestone_id.action_mark_paid()

    def _sync_to_odoo_task(self):
        """Push state update to the linked native Odoo project.task."""
        for rec in self:
            if not rec.odoo_task_id:
                continue
            stage_map = {
                'todo': 'New',
                'in_progress': 'In Progress',
                'done': 'Done',
                'blocked': 'Blocked',
                'cancelled': 'Cancelled',
            }
            stage_name = stage_map.get(rec.state, 'In Progress')
            stage = self.env['project.task.type'].search(
                [('name', 'ilike', stage_name)], limit=1,
            )
            if stage:
                rec.odoo_task_id.stage_id = stage

    def action_create_odoo_task(self):
        """Create a linked native Odoo project.task from this construction task."""
        self.ensure_one()
        if self.odoo_task_id:
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'project.task',
                'res_id': self.odoo_task_id.id,
                'view_mode': 'form',
            }
        odoo_project = self.project_id.odoo_project_id
        if not odoo_project:
            from odoo.exceptions import UserError
            raise UserError(_(
                'Please activate the project first to create an Odoo Project Task.'
            ))
        task = self.env['project.task'].create({
            'name': self.name,
            'project_id': odoo_project.id,
            'user_ids': [(4, self.responsible_id.id)] if self.responsible_id else [],
            'description': self.description or '',
            'date_deadline': self.date_end_planned,
        })
        self.odoo_task_id = task
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'project.task',
            'res_id': task.id,
            'view_mode': 'form',
        }
