# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class BudgetLine(models.Model):
    """
    Budget tracking line per cost category.
    Tracks: Approved Budget → Committed (subcontracts) → Invoiced → Paid.
    Links to Subcontractor Agreements and account.move for reconciliation.
    """
    _name = 'salaam.budget.line'
    _description = 'Project Budget Line'
    _order = 'category, name'

    project_id = fields.Many2one(
        'salaam.construction.project', string='Project',
        required=True, ondelete='cascade', index=True,
    )
    istisna_contract_id = fields.Many2one(
        related='project_id.istisna_contract_id',
        store=True,
        readonly=True,
    )
    phase_id = fields.Many2one(
        'salaam.construction.phase', string='Phase',
        domain="[('project_id','=',project_id)]",
    )
    name = fields.Char(string='Cost Item', required=True)

    category = fields.Selection([
        ('civil',           'Civil / Structural'),
        ('mep',             'MEP'),
        ('facade',          'Facade & Cladding'),
        ('fit_out',         'Fit-Out'),
        ('design',          'Design & Engineering'),
        ('supervision',     'Supervision & QA'),
        ('permits',         'Permits & Legals'),
        ('contingency',     'Contingency'),
        ('preliminaries',   'Preliminaries & Mobilisation'),
        ('other',           'Other'),
    ], string='Category', required=True)

    currency_id = fields.Many2one(
        related='project_id.currency_id', store=True,
    )

    # ── BUDGET COLUMNS ────────────────────────────────────────────────────────
    budgeted_amount = fields.Monetary(
        string='Approved Budget', currency_field='currency_id', required=True,
    )
    committed_amount = fields.Monetary(
        string='Committed (Sub-Contracts)', currency_field='currency_id',
        compute='_compute_committed', store=True,
    )
    invoiced_amount = fields.Monetary(
        string='Invoiced to Date', currency_field='currency_id',
        compute='_compute_invoiced', store=True,
    )
    spent_amount = fields.Monetary(
        string='Paid / Spent', currency_field='currency_id',
    )
    variance = fields.Monetary(
        string='Variance (Budget vs Spent)',
        compute='_compute_variance', currency_field='currency_id', store=True,
    )
    pct_spent = fields.Float(
        string='% Spent', compute='_compute_variance',
        digits=(5, 1), store=True,
    )

    # ── LINKS ─────────────────────────────────────────────────────────────────
    subcontract_id = fields.Many2one(
        'dev.contract.subcontractor',
        string='Linked Subcontract',
        domain="[('parent_istisna_id','=',istisna_contract_id)]",
    )
    invoice_ids = fields.Many2many(
        'account.move', string='Linked Invoices / Bills',
    )
    notes = fields.Text(string='Notes')

    # ── COMPUTED ──────────────────────────────────────────────────────────────
    @api.depends('subcontract_id', 'subcontract_id.subcontract_value')
    def _compute_committed(self):
        for rec in self:
            rec.committed_amount = (
                rec.subcontract_id.subcontract_value
                if rec.subcontract_id else 0
            )

    @api.depends('invoice_ids', 'invoice_ids.amount_total',
                 'invoice_ids.payment_state')
    def _compute_invoiced(self):
        for rec in self:
            rec.invoiced_amount = sum(
                inv.amount_total for inv in rec.invoice_ids
                if inv.state == 'posted'
            )

    @api.depends('budgeted_amount', 'spent_amount')
    def _compute_variance(self):
        for rec in self:
            budget = rec.budgeted_amount or 0
            spent = rec.spent_amount or 0
            rec.variance = budget - spent
            rec.pct_spent = (spent / budget * 100) if budget else 0
