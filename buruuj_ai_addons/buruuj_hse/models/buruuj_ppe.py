# -*- coding: utf-8 -*-
from odoo import models, fields, api


class BuruujPPEIssuance(models.Model):
    _name = 'buruuj.ppe.issuance'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'PPE Issuance'
    _order = 'date desc'

    name = fields.Char(compute='_compute_name', store=True)
    employee_id = fields.Many2one('hr.employee', required=True)
    employee_name = fields.Char(string='Worker (text)',
                                help='Use when employee record is not yet created.')
    project_id = fields.Many2one('project.project')
    date = fields.Date(default=fields.Date.context_today, required=True)
    item = fields.Char(required=True, string='PPE Item')
    quantity = fields.Integer(default=1)
    cost = fields.Monetary()
    issued_by = fields.Many2one('res.users', default=lambda s: s.env.user)
    notes = fields.Char()
    currency_id = fields.Many2one(
        'res.currency', default=lambda s: s.env.company.currency_id)

    @api.depends('employee_id', 'employee_name', 'item', 'date')
    def _compute_name(self):
        for rec in self:
            who = rec.employee_id.name or rec.employee_name or ''
            rec.name = f"{who} - {rec.item or ''} ({rec.date or ''})"
