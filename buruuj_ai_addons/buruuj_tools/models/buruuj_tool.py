# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class BuruujTool(models.Model):
    """Construction tool master register."""
    _name = 'buruuj.tool'
    _description = 'Construction Tool'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'code'

    name = fields.Char(string='Tool Name', required=True, tracking=True)
    code = fields.Char(string='Tool Code', required=True, copy=False, tracking=True,
                       help='Asset tag / barcode reference (e.g., DRILL-0042)')
    serial_no = fields.Char(string='Serial Number')
    category_id = fields.Many2one('buruuj.tool.category', string='Category',
                                    required=True, tracking=True)
    is_consumable = fields.Boolean(related='category_id.is_consumable', store=True)
    requires_calibration = fields.Boolean(
        related='category_id.requires_calibration', store=True)

    make = fields.Char()
    model = fields.Char()
    purchase_date = fields.Date()
    purchase_value = fields.Monetary()
    warranty_until = fields.Date()
    barcode = fields.Char(string='Barcode',
                            help='Scannable barcode for quick check-in/out.')

    # Current state
    current_location = fields.Selection([
        ('main_store', 'Main Store'),
        ('site_store', 'Site Store'),
        ('issued', 'Issued to Worker'),
        ('in_repair', 'In Repair'),
        ('in_calibration', 'In Calibration'),
        ('written_off', 'Written Off'),
        ('lost', 'Lost / Stolen'),
    ], default='main_store', required=True, tracking=True)
    current_project_id = fields.Many2one('project.project',
                                           string='Current Project / Site')
    current_holder_id = fields.Many2one('hr.employee',
                                          string='Currently Issued To')
    current_condition = fields.Selection([
        ('new', 'New'),
        ('good', 'Good'),
        ('fair', 'Fair'),
        ('poor', 'Poor'),
        ('damaged', 'Damaged'),
    ], default='good', tracking=True)

    # Calibration (only relevant when category requires it)
    last_calibration_date = fields.Date(readonly=True)
    next_calibration_due = fields.Date(string='Next Calibration Due',
                                         tracking=True, readonly=True)
    calibration_interval_months = fields.Integer(
        string='Calibration Interval (months)', default=12)
    calibration_certificate_no = fields.Char(string='Last Cert. No.', readonly=True)

    # Related
    issuance_ids = fields.One2many('buruuj.tool.issuance', 'tool_id')
    transfer_ids = fields.One2many('buruuj.tool.transfer', 'tool_id')
    calibration_ids = fields.One2many('buruuj.tool.calibration', 'tool_id')
    loss_ids = fields.One2many('buruuj.tool.loss', 'tool_id')

    # Counts
    issuance_count = fields.Integer(compute='_compute_counts')
    transfer_count = fields.Integer(compute='_compute_counts')
    calibration_count = fields.Integer(compute='_compute_counts')
    loss_count = fields.Integer(compute='_compute_counts')

    notes = fields.Text()
    active = fields.Boolean(default=True)
    currency_id = fields.Many2one(
        'res.currency', default=lambda self: self.env.company.currency_id)
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)

    _sql_constraints = [
        ('code_unique', 'unique(code, company_id)',
         'Tool code must be unique per company.'),
        ('barcode_unique', 'unique(barcode, company_id)',
         'Barcode must be unique per company.'),
    ]

    @api.depends('issuance_ids', 'transfer_ids', 'calibration_ids', 'loss_ids')
    def _compute_counts(self):
        for rec in self:
            rec.issuance_count = len(rec.issuance_ids)
            rec.transfer_count = len(rec.transfer_ids)
            rec.calibration_count = len(rec.calibration_ids)
            rec.loss_count = len(rec.loss_ids)

    def action_view_issuances(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Issuances'),
            'res_model': 'buruuj.tool.issuance',
            'view_mode': 'list,form',
            'domain': [('tool_id', '=', self.id)],
            'context': {'default_tool_id': self.id},
        }

    def action_view_calibrations(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Calibrations'),
            'res_model': 'buruuj.tool.calibration',
            'view_mode': 'list,form',
            'domain': [('tool_id', '=', self.id)],
            'context': {'default_tool_id': self.id},
        }
