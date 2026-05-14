# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class ConstructionPhase(models.Model):
    """
    A project is divided into phases (e.g. Foundation, Structure, MEP).
    Each phase has tasks, a budget allocation, and a progress tracker.
    Phases map to subcontractor agreements and Istisna milestones.
    """
    _name = 'salaam.construction.phase'
    _description = 'Construction Phase'
    _order = 'sequence, id'
    _inherit = ['mail.thread']

    name = fields.Char(string='Phase Name', required=True)
    code = fields.Char(string='Phase Code')
    sequence = fields.Integer(string='Sequence', default=10)
    project_id = fields.Many2one(
        'salaam.construction.project', string='Project',
        required=True, ondelete='cascade', index=True,
    )
    state = fields.Selection([
        ('pending',     'Not Started'),
        ('active',      'In Progress'),
        ('completed',   'Completed'),
        ('on_hold',     'On Hold'),
    ], string='Status', default='pending', tracking=True)
    istisna_contract_id = fields.Many2one(
        related='project_id.istisna_contract_id',
        string='Istisna Contract', store=False, readonly=True,
    )

    # ── PHASE CLASSIFICATION ──────────────────────────────────────────────────
    phase_type = fields.Selection([
        ('civil',           'Civil / Structural'),
        ('mep',             'MEP'),
        ('facade',          'Facade & Cladding'),
        ('fit_out',         'Interior Fit-Out'),
        ('infrastructure',  'Infrastructure / Utilities'),
        ('landscaping',     'Landscaping'),
        ('commissioning',   'Commissioning & Testing'),
        ('handover',        'Handover'),
        ('other',           'Other'),
    ], string='Phase Type', required=True)

    # ── CONTRACT LINKS ────────────────────────────────────────────────────────
    istisna_milestone_id = fields.Many2one(
        'dev.contract.milestone', string='Linked Istisna Milestone',
        domain="[('res_model','=','dev.contract.istisna')]",
        help='Links this phase to an Istisna payment milestone',
    )
    subcontract_ids = fields.Many2many(
        'dev.contract.subcontractor',
        'phase_subcontract_rel', 'phase_id', 'subcontract_id',
        string='Sub-Contracts',
    )

    # ── DATES ─────────────────────────────────────────────────────────────────
    date_start_planned = fields.Date(string='Planned Start')
    date_end_planned = fields.Date(string='Planned End')
    date_start_actual = fields.Date(string='Actual Start')
    date_end_actual = fields.Date(string='Actual End')
    delay_days = fields.Integer(
        string='Delay (days)', compute='_compute_delay', store=True,
    )

    # ── BUDGET ────────────────────────────────────────────────────────────────
    currency_id = fields.Many2one(
        related='project_id.currency_id', store=True,
    )
    budget_allocated = fields.Monetary(
        string='Allocated Budget', currency_field='currency_id',
    )
    budget_spent = fields.Monetary(
        string='Spent to Date', compute='_compute_budget_spent',
        currency_field='currency_id', store=True,
    )

    # ── PROGRESS ──────────────────────────────────────────────────────────────
    progress = fields.Float(
        string='Progress (%)', digits=(5, 1),
        tracking=True,
    )
    weight = fields.Float(
        string='Weight (%)', digits=(5, 1), default=10.0,
        help='Percentage weight this phase contributes to overall project progress',
    )

    # ── TASKS ─────────────────────────────────────────────────────────────────
    task_ids = fields.One2many(
        'salaam.construction.task', 'phase_id', string='Tasks',
    )
    task_count = fields.Integer(compute='_compute_task_count')
    completed_task_count = fields.Integer(compute='_compute_task_count')

    # ── COMPUTED ──────────────────────────────────────────────────────────────
    @api.depends('date_end_planned', 'date_end_actual', 'state')
    def _compute_delay(self):
        for rec in self:
            if rec.date_end_planned and rec.date_end_actual:
                delta = rec.date_end_actual - rec.date_end_planned
                rec.delay_days = delta.days
            elif rec.date_end_planned and rec.state not in ('completed', 'on_hold'):
                from datetime import date
                delta = date.today() - rec.date_end_planned
                rec.delay_days = max(0, delta.days)
            else:
                rec.delay_days = 0

    @api.depends('task_ids.budget_cost', 'task_ids.state')
    def _compute_budget_spent(self):
        for rec in self:
            rec.budget_spent = sum(
                t.budget_cost for t in rec.task_ids
                if t.state in ('done', 'invoiced')
            )

    @api.depends('task_ids', 'task_ids.state')
    def _compute_task_count(self):
        for rec in self:
            rec.task_count = len(rec.task_ids)
            rec.completed_task_count = len(
                rec.task_ids.filtered(lambda t: t.state in ('done', 'invoiced'))
            )

    @api.constrains('weight')
    def _check_weight(self):
        for rec in self:
            if not (0 <= rec.weight <= 100):
                raise ValidationError(_('Phase weight must be between 0 and 100%.'))

    # ── ACTIONS ───────────────────────────────────────────────────────────────
    def action_start(self):
        self.write({'state': 'active', 'date_start_actual': fields.Date.today()})

    def action_complete(self):
        self.write({'state': 'completed', 'date_end_actual': fields.Date.today(),
                    'progress': 100.0})
        # Update the linked Istisna milestone if any
        for rec in self:
            if rec.istisna_milestone_id:
                rec.istisna_milestone_id.action_mark_completed()

    def action_open_tasks(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Tasks — %s') % self.name,
            'res_model': 'salaam.construction.task',
            'view_mode': 'list,form',
            'domain': [('phase_id', '=', self.id)],
            'context': {'default_phase_id': self.id,
                        'default_project_id': self.project_id.id},
        }
