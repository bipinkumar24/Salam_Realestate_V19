# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError
from dateutil.relativedelta import relativedelta


class BuruujToolCalibration(models.Model):
    """Calibration record for instruments (theodolites, total stations, etc.)."""
    _name = 'buruuj.tool.calibration'
    _description = 'Tool Calibration'
    _inherit = ['mail.thread']
    _order = 'calibration_date desc'

    name = fields.Char(compute='_compute_name', store=True)
    tool_id = fields.Many2one('buruuj.tool', required=True, tracking=True)
    calibration_date = fields.Date(required=True,
                                     default=fields.Date.context_today, tracking=True)
    next_due_date = fields.Date(compute='_compute_next_due', store=True,
                                  readonly=False)
    certificate_no = fields.Char(string='Certificate Number', tracking=True)
    calibration_lab = fields.Char(string='Lab / Vendor')
    cost = fields.Monetary()
    result = fields.Selection([
        ('pass', 'Pass'),
        ('pass_adjustment', 'Pass with Adjustment'),
        ('fail', 'Fail'),
    ], default='pass', tracking=True)
    certificate_attachment = fields.Binary(string='Certificate (PDF)')
    certificate_filename = fields.Char()
    notes = fields.Text()
    state = fields.Selection([
        ('scheduled', 'Scheduled'),
        ('in_progress', 'In Progress'),
        ('done', 'Completed'),
        ('failed', 'Failed'),
    ], default='scheduled', tracking=True)

    currency_id = fields.Many2one(
        'res.currency', default=lambda s: s.env.company.currency_id)

    @api.depends('tool_id', 'calibration_date')
    def _compute_name(self):
        for rec in self:
            tool = rec.tool_id.name or 'Tool'
            rec.name = f"Calibration: {tool} ({rec.calibration_date or 'TBD'})"

    @api.depends('calibration_date', 'tool_id.calibration_interval_months')
    def _compute_next_due(self):
        for rec in self:
            if rec.calibration_date and rec.tool_id.calibration_interval_months:
                rec.next_due_date = rec.calibration_date + relativedelta(
                    months=rec.tool_id.calibration_interval_months)
            else:
                rec.next_due_date = False

    def action_start(self):
        for rec in self:
            rec.state = 'in_progress'
            rec.tool_id.current_location = 'in_calibration'

    def action_complete(self):
        for rec in self:
            if not rec.certificate_no and rec.result != 'fail':
                raise UserError(_(
                    'Please enter the certificate number before completion.'))
            new_state = 'failed' if rec.result == 'fail' else 'done'
            rec.state = new_state
            # Update tool master
            updates = {
                'last_calibration_date': rec.calibration_date,
                'next_calibration_due': rec.next_due_date,
                'calibration_certificate_no': rec.certificate_no,
            }
            if rec.tool_id.current_location == 'in_calibration':
                updates['current_location'] = 'main_store'
            rec.tool_id.write(updates)
