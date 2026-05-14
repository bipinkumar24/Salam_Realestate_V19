# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class ConstructionProjectHSE(models.Model):
    _inherit = 'salaam.construction.project'

    hse_incident_ids = fields.One2many('salaam.hse.incident', 'project_id', string='HSE Incidents')
    hse_rams_ids = fields.One2many('salaam.hse.method.statement', 'project_id', string='RAMS')
    hse_toolbox_ids = fields.One2many('salaam.hse.toolbox.talk', 'project_id', string='Toolbox Talks')
    hse_audit_ids = fields.One2many('salaam.hse.audit', 'project_id', string='HSE Audits')

    hse_incident_count = fields.Integer(compute='_compute_hse_counts')
    hse_lti_count = fields.Integer(compute='_compute_hse_counts', string='LTI Count')
    hse_rams_count = fields.Integer(compute='_compute_hse_counts')
    hse_toolbox_count = fields.Integer(compute='_compute_hse_counts')
    hse_audit_count = fields.Integer(compute='_compute_hse_counts')
    hse_open_rams_count = fields.Integer(compute='_compute_hse_counts')

    @api.depends(
        'hse_incident_ids', 'hse_rams_ids',
        'hse_toolbox_ids', 'hse_audit_ids',
        'hse_incident_ids.incident_type',
        'hse_rams_ids.state',
    )
    def _compute_hse_counts(self):
        for rec in self:
            rec.hse_incident_count = len(rec.hse_incident_ids)
            rec.hse_lti_count = len(
                rec.hse_incident_ids.filtered(
                    lambda i: i.incident_type in ('lost_time', 'fatality')
                )
            )
            rec.hse_rams_count = len(rec.hse_rams_ids)
            rec.hse_open_rams_count = len(
                rec.hse_rams_ids.filtered(lambda r: r.state == 'submitted')
            )
            rec.hse_toolbox_count = len(rec.hse_toolbox_ids)
            rec.hse_audit_count = len(rec.hse_audit_ids)

    def action_open_hse(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('HSE — %s') % self.name,
            'res_model': 'salaam.hse.incident',
            'view_mode': 'list,form',
            'domain': [('project_id', '=', self.id)],
            'context': {'default_project_id': self.id},
        }
