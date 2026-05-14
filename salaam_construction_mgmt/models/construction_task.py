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

    # ── COMPUTED ──────────────────────────────────────────────────────────────
    @api.depends('budget_cost', 'actual_cost')
    def _compute_cost_variance(self):
        for rec in self:
            rec.cost_variance = rec.budget_cost - rec.actual_cost

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
