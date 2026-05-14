# -*- coding: utf-8 -*-
from odoo import models, fields, api


class BuruujEquipment(models.Model):
    """Plant & Equipment master register."""
    _name = 'buruuj.equipment'
    _description = 'Plant Equipment'
    _inherit = ['mail.thread']
    _order = 'code'

    name = fields.Char(string='Equipment Name', required=True, tracking=True)
    code = fields.Char(string='Asset Code', required=True, copy=False)
    serial_no = fields.Char(string='Serial / Chassis No.')
    plate_no = fields.Char(string='Plate No.')
    category = fields.Selection([
        ('earth_moving', 'Earth Moving'),
        ('lifting', 'Lifting & Cranes'),
        ('concrete', 'Concrete Equipment'),
        ('compaction', 'Compaction'),
        ('vehicle', 'Light Vehicle'),
        ('truck', 'Heavy Truck'),
        ('generator', 'Generator / Power'),
        ('tools', 'Tools'),
        ('other', 'Other'),
    ], default='other', required=True)
    make = fields.Char()
    model = fields.Char()
    year = fields.Integer()
    ownership = fields.Selection([
        ('owned', 'Owned'),
        ('rented', 'Rented'),
        ('leased', 'Leased'),
    ], default='owned', required=True, tracking=True)
    rental_partner_id = fields.Many2one('res.partner', string='Rental Vendor')
    rental_rate_daily = fields.Monetary()
    rental_off_hire_date = fields.Date(string='Off-Hire Date')

    internal_hire_rate_daily = fields.Monetary(
        string='Internal Hire Rate (Daily)',
        help='Charged to project P&L when allocated.')

    purchase_date = fields.Date()
    purchase_value = fields.Monetary()
    current_project_id = fields.Many2one('project.project',
                                          string='Currently Allocated To')
    operator_id = fields.Many2one('hr.employee', string='Operator')
    operator_name = fields.Char(string='Operator (text)')

    state = fields.Selection([
        ('available', 'Available'),
        ('allocated', 'Allocated'),
        ('maintenance', 'Under Maintenance'),
        ('breakdown', 'Breakdown'),
        ('idle', 'Idle'),
        ('off_hire', 'Off Hire'),
    ], default='available', tracking=True)

    allocation_ids = fields.One2many('buruuj.allocation', 'equipment_id')
    fuel_log_ids = fields.One2many('buruuj.fuel.log', 'equipment_id')
    maintenance_ids = fields.One2many('buruuj.maintenance', 'equipment_id')

    notes = fields.Text()
    active = fields.Boolean(default=True)
    currency_id = fields.Many2one(
        'res.currency', default=lambda s: s.env.company.currency_id)
    company_id = fields.Many2one('res.company', default=lambda s: s.env.company)

    _sql_constraints = [
        ('code_unique', 'unique(code, company_id)',
         'Asset code must be unique per company.'),
    ]


class BuruujAllocation(models.Model):
    """Equipment allocation to project."""
    _name = 'buruuj.allocation'
    _description = 'Equipment Allocation'
    _order = 'date_from desc'

    name = fields.Char(compute='_compute_name', store=True)
    equipment_id = fields.Many2one('buruuj.equipment', required=True,
                                     ondelete='cascade')
    project_id = fields.Many2one('project.project', required=True)
    date_from = fields.Date(required=True)
    date_to = fields.Date()
    daily_rate = fields.Monetary()
    days = fields.Integer(compute='_compute_days_amount', store=True)
    amount = fields.Monetary(compute='_compute_days_amount', store=True)
    operator_id = fields.Many2one('hr.employee', string='Operator')
    notes = fields.Text()
    state = fields.Selection([
        ('active', 'Active'),
        ('returned', 'Returned'),
    ], default='active')
    currency_id = fields.Many2one(
        related='equipment_id.currency_id', store=True)

    @api.depends('equipment_id', 'project_id', 'date_from')
    def _compute_name(self):
        for rec in self:
            rec.name = (f"{rec.equipment_id.code or ''} → "
                        f"{rec.project_id.name or ''} ({rec.date_from or ''})")

    @api.depends('date_from', 'date_to', 'daily_rate')
    def _compute_days_amount(self):
        from datetime import date
        for rec in self:
            end = rec.date_to or date.today()
            if rec.date_from:
                rec.days = (end - rec.date_from).days + 1
            else:
                rec.days = 0
            rec.amount = rec.days * rec.daily_rate


class BuruujFuelLog(models.Model):
    _name = 'buruuj.fuel.log'
    _description = 'Equipment Fuel Log'
    _order = 'date desc'

    equipment_id = fields.Many2one('buruuj.equipment', required=True,
                                     ondelete='cascade')
    project_id = fields.Many2one('project.project')
    date = fields.Date(default=fields.Date.context_today, required=True)
    quantity_liters = fields.Float(string='Quantity (L)')
    unit_price = fields.Monetary()
    total_cost = fields.Monetary(compute='_compute_total', store=True)
    odometer = fields.Float(string='Odometer / Hours')
    operator = fields.Char()
    notes = fields.Char()
    currency_id = fields.Many2one(
        related='equipment_id.currency_id', store=True)

    @api.depends('quantity_liters', 'unit_price')
    def _compute_total(self):
        for rec in self:
            rec.total_cost = rec.quantity_liters * rec.unit_price


class BuruujMaintenance(models.Model):
    _name = 'buruuj.maintenance'
    _description = 'Equipment Maintenance Record'
    _order = 'date desc'

    equipment_id = fields.Many2one('buruuj.equipment', required=True,
                                     ondelete='cascade')
    date = fields.Date(default=fields.Date.context_today, required=True)
    type = fields.Selection([
        ('preventive', 'Preventive'),
        ('breakdown', 'Breakdown / Corrective'),
        ('inspection', 'Inspection'),
    ], default='preventive', required=True)
    description = fields.Text()
    next_due_date = fields.Date()
    cost = fields.Monetary()
    performed_by = fields.Char()
    state = fields.Selection([
        ('scheduled', 'Scheduled'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
    ], default='scheduled')
    currency_id = fields.Many2one(
        related='equipment_id.currency_id', store=True)
