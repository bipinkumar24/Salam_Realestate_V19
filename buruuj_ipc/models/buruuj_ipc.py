# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class BuruujIPC(models.Model):
    """Interim Payment Certificate.

    type = client → outgoing invoice to client
    type = subcontractor → incoming bill from subcontractor"""
    _name = 'buruuj.ipc'
    _description = 'Interim Payment Certificate'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date desc, id desc'

    name = fields.Char(copy=False, default=lambda s: _('New'), tracking=True)
    type = fields.Selection([
        ('client', 'Client IPC'),
        ('subcontractor', 'Subcontractor IPC'),
    ], required=True, default='client', tracking=True)
    sequence_no = fields.Integer(string='IPC No.', default=1,
                                  help='Running sequence per project / subcontract.')

    project_id = fields.Many2one('project.project', required=True, tracking=True)
    partner_id = fields.Many2one('res.partner', required=True, tracking=True)
    subcontract_id = fields.Many2one('buruuj.subcontract', tracking=True,
                                      domain="[('partner_id','=',partner_id)]")

    date = fields.Date(default=fields.Date.context_today, tracking=True)
    period_from = fields.Date()
    period_to = fields.Date()

    line_ids = fields.One2many('buruuj.ipc.line', 'ipc_id', string='Lines')

    # Amounts
    work_done_amount = fields.Monetary(
        string='Work Done This Period', compute='_compute_amounts', store=True)
    cumulative_amount = fields.Monetary(
        string='Cumulative Work Done', compute='_compute_amounts', store=True)
    previous_certified = fields.Monetary(string='Previously Certified')
    materials_on_site = fields.Monetary(string='Materials on Site')

    # Retention & advance
    retention_percent = fields.Float(string='Retention %', default=10.0)
    retention_amount = fields.Monetary(compute='_compute_amounts', store=True)
    advance_recovery_percent = fields.Float(string='Advance Recovery %', default=20.0)
    advance_recovery_amount = fields.Monetary(compute='_compute_amounts', store=True)
    backcharge_amount = fields.Monetary(string='Back-charges')

    gross_amount = fields.Monetary(compute='_compute_amounts', store=True)
    net_amount = fields.Monetary(compute='_compute_amounts', store=True)
    vat_amount = fields.Monetary(string='VAT')
    total_payable = fields.Monetary(compute='_compute_amounts', store=True)

    state = fields.Selection([
        ('draft', 'Draft'),
        ('qs_approved', 'QS Approved'),
        ('pm_approved', 'PM Approved'),
        ('finance_approved', 'Finance Approved'),
        ('paid', 'Paid'),
        ('rejected', 'Rejected'),
    ], default='draft', tracking=True)

    qs_id = fields.Many2one('res.users', string='QS', tracking=True)
    pm_id = fields.Many2one('res.users', string='PM', tracking=True)
    finance_id = fields.Many2one('res.users', string='Finance', tracking=True)

    notes = fields.Html()
    currency_id = fields.Many2one(
        'res.currency', default=lambda s: s.env.company.currency_id)
    company_id = fields.Many2one('res.company', default=lambda s: s.env.company)

    @api.depends('line_ids.amount', 'previous_certified', 'materials_on_site',
                 'retention_percent', 'advance_recovery_percent',
                 'backcharge_amount', 'vat_amount')
    def _compute_amounts(self):
        for rec in self:
            cumulative = sum(rec.line_ids.mapped('cumulative_amount'))
            rec.cumulative_amount = cumulative
            rec.work_done_amount = cumulative - rec.previous_certified
            base = rec.work_done_amount + rec.materials_on_site
            rec.retention_amount = base * rec.retention_percent / 100.0
            rec.advance_recovery_amount = (rec.work_done_amount
                                            * rec.advance_recovery_percent / 100.0)
            rec.gross_amount = base
            rec.net_amount = (base - rec.retention_amount
                              - rec.advance_recovery_amount - rec.backcharge_amount)
            rec.total_payable = rec.net_amount + rec.vat_amount

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                code = ('buruuj.ipc.client' if vals.get('type') == 'client'
                        else 'buruuj.ipc.subcontractor')
                vals['name'] = self.env['ir.sequence'].next_by_code(code) or _('New')
        return super().create(vals_list)

    # ---- Workflow ----
    def action_qs_approve(self):
        for rec in self:
            if rec.net_amount < 0:
                raise UserError(_('Net amount cannot be negative.'))
            rec.write({'state': 'qs_approved', 'qs_id': self.env.user.id})

    def action_pm_approve(self):
        self.write({'state': 'pm_approved', 'pm_id': self.env.user.id})

    def action_finance_approve(self):
        self.write({'state': 'finance_approved', 'finance_id': self.env.user.id})

    def action_mark_paid(self):
        self.state = 'paid'

    def action_reject(self):
        self.state = 'rejected'

    def action_reset(self):
        self.state = 'draft'


class BuruujIPCLine(models.Model):
    _name = 'buruuj.ipc.line'
    _description = 'IPC Line'
    _order = 'sequence, id'

    sequence = fields.Integer(default=10)
    ipc_id = fields.Many2one('buruuj.ipc', required=True, ondelete='cascade')
    item_no = fields.Char()
    description = fields.Text(required=True)
    uom_id = fields.Many2one('uom.uom')
    contract_qty = fields.Float(string='Contract Qty')
    unit_rate = fields.Monetary()
    cumulative_qty = fields.Float(string='Cumulative Qty Done')
    previous_qty = fields.Float()
    period_qty = fields.Float(compute='_compute_period_qty', store=True)
    cumulative_amount = fields.Monetary(compute='_compute_amount', store=True)
    amount = fields.Monetary(string='This Period', compute='_compute_amount', store=True)
    currency_id = fields.Many2one(related='ipc_id.currency_id', store=True)

    @api.depends('cumulative_qty', 'previous_qty')
    def _compute_period_qty(self):
        for rec in self:
            rec.period_qty = rec.cumulative_qty - rec.previous_qty

    @api.depends('cumulative_qty', 'previous_qty', 'unit_rate')
    def _compute_amount(self):
        for rec in self:
            rec.cumulative_amount = rec.cumulative_qty * rec.unit_rate
            rec.amount = rec.period_qty * rec.unit_rate
