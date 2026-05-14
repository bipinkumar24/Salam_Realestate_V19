# -*- coding: utf-8 -*-
from odoo import models, fields, api


class BuruujRisk(models.Model):
    """Project risk register."""
    _name = 'buruuj.risk'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Project Risk'
    _order = 'severity desc, id desc'

    name = fields.Char(string='Risk Title', required=True)
    project_id = fields.Many2one('project.project', required=True, ondelete='cascade')
    category = fields.Selection([
        ('schedule', 'Schedule'),
        ('cost', 'Cost'),
        ('quality', 'Quality'),
        ('safety', 'Safety'),
        ('contract', 'Contract / Legal'),
        ('weather', 'Weather'),
        ('political', 'Political / Regulatory'),
        ('other', 'Other'),
    ], default='other')
    description = fields.Text()
    likelihood = fields.Selection([
        ('1', 'Very Low'), ('2', 'Low'), ('3', 'Medium'),
        ('4', 'High'), ('5', 'Very High'),
    ], default='3')
    impact = fields.Selection([
        ('1', 'Very Low'), ('2', 'Low'), ('3', 'Medium'),
        ('4', 'High'), ('5', 'Very High'),
    ], default='3')
    severity = fields.Integer(compute='_compute_severity', store=True)
    mitigation = fields.Text(string='Mitigation Plan')
    owner_id = fields.Many2one('res.users', string='Owner')
    state = fields.Selection([
        ('open', 'Open'),
        ('mitigated', 'Mitigated'),
        ('realized', 'Realized'),
        ('closed', 'Closed'),
    ], default='open')

    @api.depends('likelihood', 'impact')
    def _compute_severity(self):
        for rec in self:
            try:
                rec.severity = int(rec.likelihood) * int(rec.impact)
            except (TypeError, ValueError):
                rec.severity = 0
