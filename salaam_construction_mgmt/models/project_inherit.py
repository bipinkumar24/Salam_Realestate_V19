# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class ProjectProjectInherit(models.Model):
    """Add reverse link from native Odoo project back to Salaam construction project."""
    _inherit = 'project.project'

    salaam_project_id = fields.Many2one(
        'salaam.construction.project',
        string='Salaam Construction Project',
        ondelete='set null',
        readonly=True,
    )
    is_construction_project = fields.Boolean(
        string='Construction Project',
        compute='_compute_is_construction',
        store=True,
    )

    @api.depends('salaam_project_id')
    def _compute_is_construction(self):
        for rec in self:
            rec.is_construction_project = bool(rec.salaam_project_id)


class ProjectTaskInherit(models.Model):
    """Add reverse link from native Odoo task back to Salaam construction task."""
    _inherit = 'project.task'

    salaam_task_id = fields.Many2one(
        'salaam.construction.task',
        string='Salaam Construction Task',
        ondelete='set null',
        readonly=True,
    )
