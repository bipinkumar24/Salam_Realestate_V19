# -*- coding: utf-8 -*-
from odoo import models, fields, api


class SalaamProject(models.Model):
    """
    Development / Master Project.
    e.g. "Salaam City Phase 1", "FN Block", "Al Noor Residences"
    """
    _name = 'salaam.project'
    _description = 'Development / Project'
    _order = 'name'

    name = fields.Char(string='Project Name', required=True)
    code = fields.Char(string='Code')
    description = fields.Text(string='Description')
    active = fields.Boolean(default=True)

    sub_project_ids = fields.One2many(
        'salaam.sub.project', 'project_id',
        string='Sub Projects',
    )
    sub_project_count = fields.Integer(
        compute='_compute_sub_project_count', string='Sub Projects'
    )
    property_count = fields.Integer(
        compute='_compute_property_count', string='Units'
    )

    @api.depends('sub_project_ids')
    def _compute_sub_project_count(self):
        for rec in self:
            rec.sub_project_count = len(rec.sub_project_ids)

    def _compute_property_count(self):
        for rec in self:
            rec.property_count = self.env['property.details'].search_count([
                ('salaam_project_id', '=', rec.id)
            ])


class SalaamSubProject(models.Model):
    """
    Sub Project / Block / Phase within a Development.
    e.g. "Block A", "Tower 1", "Phase 2"
    """
    _name = 'salaam.sub.project'
    _description = 'Sub Project / Block'
    _order = 'project_id, name'

    name = fields.Char(string='Sub Project Name', required=True)
    code = fields.Char(string='Code')
    project_id = fields.Many2one(
        'salaam.project', string='Development / Project',
        required=True, ondelete='cascade',
    )
    active = fields.Boolean(default=True)

    property_count = fields.Integer(
        compute='_compute_property_count', string='Units'
    )

    def _compute_property_count(self):
        for rec in self:
            rec.property_count = self.env['property.details'].search_count([
                ('salaam_sub_project_id', '=', rec.id)
            ])


class PropertyDetailsProjectInherit(models.Model):
    """
    Extends property.details with Salaam project and sub-project Many2one fields.
    """
    _inherit = 'property.details'

    salaam_project_id = fields.Many2one(
        'salaam.project',
        string='Development / Project',
        index=True,
    )
    salaam_sub_project_id = fields.Many2one(
        'salaam.sub.project',
        string='Sub Project',
        domain="[('project_id', '=', salaam_project_id)]",
        index=True,
    )
