# -*- coding: utf-8 -*-
from odoo import models, fields, api


class ResUsers(models.Model):
    _inherit = 'res.users'

    user_role = fields.Selection([
        ('real_estate_agent', 'Real Estate Agent'),
        ('bank_officer', 'Bank Officer'),
        ('manager', 'Manager'),
    ], string='Platform Role', default='real_estate_agent')

    agent_license_no = fields.Char(string='Agent License No.')
    bank_branch = fields.Char(string='Bank Branch')
    bank_employee_id = fields.Char(string='Bank Employee ID')
    is_sharia_certified = fields.Boolean(string='Sharia Certified Officer')

    @property
    def is_real_estate_agent(self):
        return self.user_role == 'real_estate_agent'

    @property
    def is_bank_officer(self):
        return self.user_role == 'bank_officer'
