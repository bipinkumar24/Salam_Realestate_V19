# -*- coding: utf-8 -*-
from odoo import fields, models


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    cv_attachment_id = fields.Many2one(
        'ir.attachment', string='CV / Resume',
        help='Latest curriculum vitae for tender submissions.',
    )
    bid_availability_state = fields.Selection([
        ('available', 'Available'),
        ('partially', 'Partially Allocated'),
        ('unavailable', 'Unavailable'),
        ('on_leave', 'On Leave'),
    ], string='Bid Availability', default='available')
    is_key_personnel = fields.Boolean(
        string='Key Personnel',
        help='Eligible to be listed as key personnel in tender proposals.',
    )
    bid_skill_summary = fields.Text(
        string='Bid Skills Summary',
        help='Concise list of skills relevant to tendering.',
    )
