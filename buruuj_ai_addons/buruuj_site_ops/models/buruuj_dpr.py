# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class BuruujDPR(models.Model):
    """Daily Progress Report — captured on site each day."""
    _name = 'buruuj.dpr'
    _description = 'Daily Progress Report'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date desc, id desc'

    name = fields.Char(copy=False, default=lambda s: _('New'), tracking=True)
    project_id = fields.Many2one('project.project', required=True, tracking=True)
    date = fields.Date(default=fields.Date.context_today, required=True, tracking=True)
    reported_by = fields.Many2one('res.users', default=lambda s: s.env.user,
                                   tracking=True)

    # Weather
    weather = fields.Selection([
        ('clear', 'Clear'),
        ('cloudy', 'Cloudy'),
        ('rain', 'Rain'),
        ('storm', 'Storm'),
        ('hot', 'Extreme Heat'),
        ('cold', 'Extreme Cold'),
    ], default='clear')
    temperature = fields.Float(string='Temperature (°C)')
    humidity = fields.Float(string='Humidity (%)')
    rain_hours = fields.Float(string='Lost Hours due to Weather')

    # Resources
    manpower_line_ids = fields.One2many('buruuj.dpr.manpower', 'dpr_id',
                                          string='Manpower')
    equipment_line_ids = fields.One2many('buruuj.dpr.equipment', 'dpr_id',
                                           string='Equipment Deployed')
    total_workers = fields.Integer(compute='_compute_totals', store=True)
    total_equipment = fields.Integer(compute='_compute_totals', store=True)

    # Work
    work_executed = fields.Html(string='Work Executed Today')
    delays_issues = fields.Html(string='Delays / Issues')
    visitors = fields.Char(string='Site Visitors')

    # Geo
    site_lat = fields.Float(digits=(10, 6))
    site_lng = fields.Float(digits=(10, 6))

    state = fields.Selection([
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('approved', 'Approved'),
    ], default='draft', tracking=True)

    @api.depends('manpower_line_ids.count', 'equipment_line_ids.count')
    def _compute_totals(self):
        for rec in self:
            rec.total_workers = sum(rec.manpower_line_ids.mapped('count'))
            rec.total_equipment = sum(rec.equipment_line_ids.mapped('count'))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'buruuj.dpr') or _('New')
        return super().create(vals_list)

    def action_submit(self):
        self.state = 'submitted'

    def action_approve(self):
        self.state = 'approved'

    def action_reset(self):
        self.state = 'draft'


class BuruujDPRManpower(models.Model):
    _name = 'buruuj.dpr.manpower'
    _description = 'DPR Manpower Line'

    dpr_id = fields.Many2one('buruuj.dpr', required=True, ondelete='cascade')
    trade_id = fields.Many2one('buruuj.trade', string='Trade', required=True)
    subcontractor_id = fields.Many2one('res.partner',
                                         domain=[('is_subcontractor', '=', True)])
    count = fields.Integer(string='Number of Workers', required=True, default=1)
    hours = fields.Float(string='Hours Worked', default=8.0)
    notes = fields.Char()


class BuruujDPREquipment(models.Model):
    _name = 'buruuj.dpr.equipment'
    _description = 'DPR Equipment Line'

    dpr_id = fields.Many2one('buruuj.dpr', required=True, ondelete='cascade')
    equipment_type = fields.Char(required=True)
    count = fields.Integer(default=1)
    hours_used = fields.Float()
    operator = fields.Char()
    notes = fields.Char()
