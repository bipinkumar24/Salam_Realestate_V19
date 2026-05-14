# -*- coding: utf-8 -*-
from odoo import models, fields, api


class BuruujBOQ(models.Model):
    """Bill of Quantities header. Holds the hierarchical structure of items."""
    _name = 'buruuj.boq'
    _description = 'Bill of Quantities'
    _inherit = ['mail.thread']
    _order = 'id desc'

    name = fields.Char(string='BOQ Reference', required=True, default='Draft BOQ')
    tender_id = fields.Many2one('buruuj.tender', string='Tender', ondelete='cascade')
    project_id = fields.Many2one('project.project', string='Project',
                                 ondelete='set null')
    revision = fields.Char(string='Revision', default='R0')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('frozen', 'Frozen / Baseline'),
    ], default='draft', tracking=True)

    section_ids = fields.One2many('buruuj.boq.section', 'boq_id', string='Sections')
    line_ids = fields.One2many('buruuj.boq.line', 'boq_id', string='All Lines')

    total_amount = fields.Monetary(
        string='Total Amount', compute='_compute_total', store=True)
    line_count = fields.Integer(compute='_compute_total')
    currency_id = fields.Many2one(
        'res.currency', default=lambda self: self.env.company.currency_id)
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)

    @api.depends('line_ids.amount')
    def _compute_total(self):
        for rec in self:
            rec.total_amount = sum(rec.line_ids.mapped('amount'))
            rec.line_count = len(rec.line_ids)

    def action_confirm(self):
        self.state = 'confirmed'

    def action_freeze(self):
        self.state = 'frozen'


class BuruujBOQSection(models.Model):
    """Hierarchical section within a BOQ (e.g., Substructure → Concrete Works)."""
    _name = 'buruuj.boq.section'
    _description = 'BOQ Section'
    _order = 'sequence, code'

    name = fields.Char(string='Section Name', required=True)
    code = fields.Char(string='Code', required=True, help='e.g. 2.1.3')
    sequence = fields.Integer(default=10)
    boq_id = fields.Many2one('buruuj.boq', required=True, ondelete='cascade')
    parent_id = fields.Many2one('buruuj.boq.section', ondelete='cascade')
    child_ids = fields.One2many('buruuj.boq.section', 'parent_id')
    line_ids = fields.One2many('buruuj.boq.line', 'section_id')
    section_amount = fields.Monetary(
        compute='_compute_section_amount', store=True)
    currency_id = fields.Many2one(related='boq_id.currency_id', store=True)

    @api.depends('line_ids.amount')
    def _compute_section_amount(self):
        for rec in self:
            rec.section_amount = sum(rec.line_ids.mapped('amount'))


class BuruujBOQLine(models.Model):
    """Individual BOQ line item with quantity, unit rate, and rate breakdown."""
    _name = 'buruuj.boq.line'
    _description = 'BOQ Line Item'
    _order = 'sequence, id'

    sequence = fields.Integer(default=10)
    boq_id = fields.Many2one('buruuj.boq', required=True, ondelete='cascade')
    section_id = fields.Many2one('buruuj.boq.section', ondelete='cascade')
    item_no = fields.Char(string='Item No.', required=True)
    description = fields.Text(string='Description', required=True)

    uom_id = fields.Many2one('uom.uom', string='UoM', required=True)
    quantity = fields.Float(string='Quantity', default=0.0)

    # Rate breakdown
    rate_id = fields.Many2one(
        'buruuj.rate', string='Master Rate',
        help='Reference to master rate. Selecting one populates the unit rate.')
    labor_cost = fields.Monetary(string='Labor Cost / unit')
    material_cost = fields.Monetary(string='Material Cost / unit')
    equipment_cost = fields.Monetary(string='Equipment Cost / unit')
    subcontract_cost = fields.Monetary(string='Subcontract Cost / unit')
    wastage_percent = fields.Float(string='Wastage %', default=0.0)

    unit_rate = fields.Monetary(string='Unit Rate',
                                compute='_compute_unit_rate', store=True, readonly=False)
    amount = fields.Monetary(string='Amount',
                             compute='_compute_amount', store=True)

    trade_id = fields.Many2one('buruuj.trade', string='Trade')
    notes = fields.Char(string='Notes')
    currency_id = fields.Many2one(related='boq_id.currency_id', store=True)

    @api.onchange('rate_id')
    def _onchange_rate_id(self):
        if self.rate_id:
            self.unit_rate = self.rate_id.unit_rate
            if not self.uom_id:
                self.uom_id = self.rate_id.uom_id
            if not self.trade_id:
                self.trade_id = self.rate_id.trade_id

    @api.depends('labor_cost', 'material_cost', 'equipment_cost',
                 'subcontract_cost', 'wastage_percent')
    def _compute_unit_rate(self):
        for rec in self:
            base = (rec.labor_cost + rec.material_cost
                    + rec.equipment_cost + rec.subcontract_cost)
            if base:
                rec.unit_rate = base * (1.0 + (rec.wastage_percent / 100.0))

    @api.depends('quantity', 'unit_rate')
    def _compute_amount(self):
        for rec in self:
            rec.amount = rec.quantity * rec.unit_rate
