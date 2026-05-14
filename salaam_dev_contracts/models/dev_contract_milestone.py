# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class DevContractMilestone(models.Model):
    _name = 'dev.contract.milestone'
    _description = 'Contract Payment Milestone'
    _order = 'sequence, planned_date'

    name = fields.Char(string='Milestone', required=True)
    sequence = fields.Integer(string='Sequence', default=10)

    # Direct Many2one back-reference (required for One2many inverse)
    contract_id = fields.Many2one(
        'dev.contract.base', string='Contract', ondelete='cascade', index=True,
    )
    # Generic reference — kept for compatibility
    res_model = fields.Char(
        string='Contract Model',
        compute='_compute_res_fields', store=True, readonly=False,
    )
    res_id = fields.Integer(
        string='Contract ID',
        compute='_compute_res_fields', store=True, readonly=False,
    )

    planned_date = fields.Date(string='Planned Date', required=True)
    actual_date = fields.Date(string='Actual Completion Date')

    currency_id = fields.Many2one(
        'res.currency', string='Currency',
        default=lambda self: self.env.ref('base.USD'),
    )
    payment_amount = fields.Monetary(
        string='Payment Amount', currency_field='currency_id', required=True,
    )
    payment_pct = fields.Float(
        string='% of Contract', digits=(5, 2),
        compute='_compute_payment_pct', store=True,
    )
    retention_held = fields.Monetary(
        string='Retention Held', currency_field='currency_id',
    )
    net_payable = fields.Monetary(
        string='Net Payable', compute='_compute_net_payable',
        currency_field='currency_id', store=True,
    )

    state = fields.Selection(
        selection=[
            ('pending', 'Pending'),
            ('in_progress', 'In Progress'),
            ('completed', 'Completed'),
            ('paid', 'Paid'),
            ('overdue', 'Overdue'),
        ],
        string='Status', default='pending', required=True, tracking=True,
    )

    invoice_id = fields.Many2one(
        'account.move', string='Invoice / Bill', ondelete='set null',
    )
    verified_by = fields.Many2one('res.users', string='Verified By')
    notes = fields.Text(string='Notes')

    @api.depends('contract_id')
    def _compute_res_fields(self):
        for rec in self:
            if rec.contract_id:
                rec.res_model = rec.contract_id._name
                rec.res_id    = rec.contract_id.id
            else:
                rec.res_model = rec.res_model or False
                rec.res_id    = rec.res_id    or 0

    @api.depends('payment_amount', 'res_id', 'res_model')
    def _compute_payment_pct(self):
        for rec in self:
            if rec.res_model and rec.res_id:
                try:
                    contract = self.env[rec.res_model].browse(rec.res_id)
                    total = getattr(contract, 'contract_value', 0) or 0
                    rec.payment_pct = (rec.payment_amount / total * 100) if total else 0
                except Exception:
                    rec.payment_pct = 0
            else:
                rec.payment_pct = 0

    @api.depends('payment_amount', 'retention_held')
    def _compute_net_payable(self):
        for rec in self:
            rec.net_payable = rec.payment_amount - (rec.retention_held or 0)

    def action_mark_completed(self):
        self.write({'state': 'completed', 'actual_date': fields.Date.today()})

    def action_mark_paid(self):
        self.write({'state': 'paid'})

    def action_create_invoice(self):
        """Scaffold a vendor bill for this milestone payment."""
        self.ensure_one()
        if self.invoice_id:
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'account.move',
                'res_id': self.invoice_id.id,
                'view_mode': 'form',
            }
        invoice = self.env['account.move'].create({
            'move_type': 'in_invoice',
            'invoice_date': fields.Date.today(),
            'invoice_line_ids': [(0, 0, {
                'name': '%s — %s' % (self.name, self.res_model),
                'quantity': 1,
                'price_unit': self.net_payable,
            })],
        })
        self.invoice_id = invoice
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'res_id': invoice.id,
            'view_mode': 'form',
        }
