# -*- coding: utf-8 -*-
from odoo import models, fields, api


class BuruujWBS(models.Model):
    """Work Breakdown Structure."""
    _name = 'buruuj.wbs'
    _description = 'Work Breakdown Structure'
    _parent_store = True
    _order = 'parent_path, sequence, id'

    name = fields.Char(string='Activity', required=True)
    code = fields.Char(string='WBS Code', required=True, help='e.g. 1.2.3')
    sequence = fields.Integer(default=10)
    project_id = fields.Many2one('project.project', required=True, ondelete='cascade')
    phase_id = fields.Many2one('buruuj.phase')
    parent_id = fields.Many2one('buruuj.wbs', ondelete='cascade')
    parent_path = fields.Char(index=True)
    child_ids = fields.One2many('buruuj.wbs', 'parent_id')
    trade_id = fields.Many2one('buruuj.trade')

    # Estimated vs actual
    planned_qty = fields.Float(string='Planned Qty')
    actual_qty = fields.Float(string='Executed Qty')
    uom_id = fields.Many2one('uom.uom', string='UoM')
    planned_cost = fields.Monetary(string='Planned Cost')
    actual_cost = fields.Monetary(string='Actual Cost')
    progress = fields.Float(string='Progress %', compute='_compute_progress', store=True)

    planned_start = fields.Date()
    planned_end = fields.Date()
    actual_start = fields.Date()
    actual_end = fields.Date()

    currency_id = fields.Many2one(
        'res.currency', default=lambda self: self.env.company.currency_id)

    @api.depends('planned_qty', 'actual_qty')
    def _compute_progress(self):
        for rec in self:
            rec.progress = (100.0 * rec.actual_qty / rec.planned_qty) if rec.planned_qty else 0.0
