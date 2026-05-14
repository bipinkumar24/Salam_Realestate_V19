# -*- coding: utf-8 -*-
from odoo import fields, models


class BoqLine(models.Model):
    _inherit = 'ai.boq.line'

    master_rate_id = fields.Many2one(
        'buruuj.rate', string='Master Rate', ondelete='set null',
        help='Buruuj master-rate entry that priced this line.')
