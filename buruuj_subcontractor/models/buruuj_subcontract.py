# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError
from dateutil.relativedelta import relativedelta


class BuruujSubcontract(models.Model):
    """Subcontract agreement between Buruuj and a subcontractor."""
    _name = 'buruuj.subcontract'
    _description = 'Subcontract Agreement'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date desc, id desc'

    name = fields.Char(string='Subcontract No.', copy=False,
                       default=lambda s: _('New'), tracking=True)
    title = fields.Char(string='Subcontract Title', required=True, tracking=True)
    project_id = fields.Many2one('project.project', required=True, tracking=True,
                                  ondelete='restrict')
    partner_id = fields.Many2one(
        'res.partner', string='Subcontractor', required=True, tracking=True,
        domain=[('is_subcontractor', '=', True)])
    trade_id = fields.Many2one('buruuj.trade', string='Trade', required=True)

    date = fields.Date(default=fields.Date.context_today, tracking=True)
    start_date = fields.Date(string='Start Date', tracking=True)
    end_date = fields.Date(string='Completion Date', tracking=True)
    dlp_months = fields.Integer(string='DLP (months)', default=12)
    dlp_end = fields.Date(compute='_compute_dlp_end', store=True)

    contract_value = fields.Monetary(string='Contract Value', tracking=True)
    advance_percent = fields.Float(
        string='Advance %',
        default=lambda s: float(s.env['ir.config_parameter'].sudo().get_param(
            'buruuj.default_advance_percent') or 20.0))
    retention_percent = fields.Float(
        string='Retention %',
        default=lambda s: float(s.env['ir.config_parameter'].sudo().get_param(
            'buruuj.default_retention_percent') or 10.0))
    advance_amount = fields.Monetary(compute='_compute_advance_retention', store=True)
    retention_amount = fields.Monetary(compute='_compute_advance_retention', store=True)

    payment_terms = fields.Selection([
        ('milestone', 'Milestone-based'),
        ('progress', 'Progress (% completion)'),
        ('lump_sum', 'Lump Sum'),
    ], default='progress', tracking=True)

    scope_of_work = fields.Html(string='Scope of Work')
    line_ids = fields.One2many('buruuj.subcontract.line', 'subcontract_id',
                                string='Lines / BOQ')
    workorder_ids = fields.One2many('buruuj.workorder', 'subcontract_id',
                                     string='Work Orders')

    # Bonds & insurance
    performance_bond_amount = fields.Monetary(string='Performance Bond')
    performance_bond_expiry = fields.Date(string='Bond Expiry')
    insurance_expiry = fields.Date()

    # LD
    ld_percent_per_day = fields.Float(string='LD % per day')
    ld_cap_percent = fields.Float(string='LD Cap %', default=10.0)

    state = fields.Selection([
        ('draft', 'Draft'),
        ('approved', 'Approved'),
        ('signed', 'Signed'),
        ('in_progress', 'In Progress'),
        ('completed', 'Practically Complete'),
        ('dlp', 'In DLP'),
        ('closed', 'Closed'),
        ('terminated', 'Terminated'),
    ], default='draft', tracking=True)

    currency_id = fields.Many2one(
        'res.currency', default=lambda self: self.env.company.currency_id)
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)

    # Counts
    workorder_count = fields.Integer(compute='_compute_counts')
    ipc_count = fields.Integer(compute='_compute_counts')
    backcharge_count = fields.Integer(compute='_compute_counts')

    @api.depends('workorder_ids')
    def _compute_counts(self):
        for rec in self:
            rec.workorder_count = len(rec.workorder_ids)
            rec.ipc_count = self.env['buruuj.ipc'].search_count(
                [('subcontract_id', '=', rec.id)]) if 'buruuj.ipc' in self.env else 0
            rec.backcharge_count = self.env['buruuj.backcharge'].search_count(
                [('subcontract_id', '=', rec.id)])

    @api.depends('contract_value', 'advance_percent', 'retention_percent')
    def _compute_advance_retention(self):
        for rec in self:
            rec.advance_amount = rec.contract_value * rec.advance_percent / 100.0
            rec.retention_amount = rec.contract_value * rec.retention_percent / 100.0

    @api.depends('end_date', 'dlp_months')
    def _compute_dlp_end(self):
        for rec in self:
            if rec.end_date and rec.dlp_months:
                rec.dlp_end = rec.end_date + relativedelta(months=rec.dlp_months)
            else:
                rec.dlp_end = False

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'buruuj.subcontract') or _('New')
        return super().create(vals_list)

    # ---- Workflow ----
    def action_approve(self):
        for rec in self:
            if not rec.partner_id.trade_license_no:
                raise UserError(_(
                    'Cannot approve a subcontract for a partner without a Trade License No.'))
        self.state = 'approved'

    def action_sign(self):
        self.state = 'signed'

    def action_start(self):
        self.state = 'in_progress'

    def action_complete(self):
        self.state = 'completed'

    def action_enter_dlp(self):
        self.state = 'dlp'

    def action_close(self):
        self.state = 'closed'

    def action_terminate(self):
        self.state = 'terminated'

    def action_view_workorders(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Work Orders'),
            'res_model': 'buruuj.workorder',
            'view_mode': 'list,form',
            'domain': [('subcontract_id', '=', self.id)],
            'context': {'default_subcontract_id': self.id,
                        'default_partner_id': self.partner_id.id,
                        'default_project_id': self.project_id.id},
        }


class BuruujSubcontractLine(models.Model):
    _name = 'buruuj.subcontract.line'
    _description = 'Subcontract BOQ Line'
    _order = 'sequence, id'

    sequence = fields.Integer(default=10)
    subcontract_id = fields.Many2one('buruuj.subcontract', required=True,
                                      ondelete='cascade')
    project_id = fields.Many2one(
        related='subcontract_id.project_id', store=True)
    boq_line_id = fields.Many2one(
        'buruuj.boq.line', string='BOQ Item',
        domain="[('boq_id.project_id', '=', project_id)]",
        help='Link to the BOQ line this scope is drawn from. Selecting one '
             'pre-fills item no., description, UoM and unit rate.')
    item_no = fields.Char(string='Item No.')
    description = fields.Text(required=True)
    uom_id = fields.Many2one('uom.uom', string='UoM')
    quantity = fields.Float()
    unit_rate = fields.Monetary()
    amount = fields.Monetary(compute='_compute_amount', store=True)
    currency_id = fields.Many2one(related='subcontract_id.currency_id', store=True)

    @api.onchange('boq_line_id')
    def _onchange_boq_line_id(self):
        if self.boq_line_id:
            self.item_no = self.boq_line_id.item_no
            self.description = self.boq_line_id.description
            self.uom_id = self.boq_line_id.uom_id
            if not self.quantity:
                self.quantity = self.boq_line_id.quantity
            if not self.unit_rate:
                self.unit_rate = self.boq_line_id.subcontract_cost or self.boq_line_id.unit_rate

    @api.depends('quantity', 'unit_rate')
    def _compute_amount(self):
        for rec in self:
            rec.amount = rec.quantity * rec.unit_rate
