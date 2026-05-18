# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class ConstructionProjectContractorMgmt(models.Model):
    _inherit = 'project.project'

    # ── ONE2MANY LINKS ────────────────────────────────────────────────────────
    site_instruction_ids = fields.One2many(
        'salaam.site.instruction', 'project_id', string='Site Instructions',
    )
    ncr_ids = fields.One2many(
        'salaam.ncr', 'project_id', string='NCRs',
    )
    eot_claim_ids = fields.One2many(
        'salaam.eot.claim', 'project_id', string='EOT Claims',
    )
    contractor_programme_ids = fields.One2many(
        'salaam.contractor.programme', 'project_id', string='Programmes',
    )

    # ── SMART BUTTON COUNTS ───────────────────────────────────────────────────
    si_count = fields.Integer(compute='_compute_contractor_counts', string='Site Instructions')
    ncr_count = fields.Integer(compute='_compute_contractor_counts', string='NCRs')
    open_ncr_count = fields.Integer(compute='_compute_contractor_counts', string='Open NCRs')
    critical_ncr_count = fields.Integer(compute='_compute_contractor_counts', string='Critical NCRs')
    eot_count = fields.Integer(compute='_compute_contractor_counts', string='EOT Claims')
    eot_total_granted = fields.Integer(compute='_compute_contractor_counts', string='EOT Days Granted')
    programme_count = fields.Integer(compute='_compute_contractor_counts', string='Programmes')
    approved_programme_id = fields.Many2one(
        'salaam.contractor.programme',
        compute='_compute_contractor_counts',
        string='Current Approved Programme',
        store=True,
    )
    programme_in_delay = fields.Boolean(
        compute='_compute_contractor_counts',
        string='Programme In Delay',
        store=True,
    )

    @api.depends(
        'site_instruction_ids',
        'ncr_ids', 'ncr_ids.state', 'ncr_ids.severity',
        'eot_claim_ids', 'eot_claim_ids.state', 'eot_claim_ids.days_granted',
        'contractor_programme_ids', 'contractor_programme_ids.state',
        'contractor_programme_ids.is_in_delay',
    )
    def _compute_contractor_counts(self):
        for rec in self:
            rec.si_count = len(rec.site_instruction_ids)
            ncrs = rec.ncr_ids
            rec.ncr_count = len(ncrs)
            rec.open_ncr_count = len(ncrs.filtered(
                lambda n: n.state not in ('closed', 'rejected_permanent')
            ))
            rec.critical_ncr_count = len(ncrs.filtered(
                lambda n: n.severity == 'critical' and n.state not in ('closed', 'rejected_permanent')
            ))
            eots = rec.eot_claim_ids
            rec.eot_count = len(eots)
            rec.eot_total_granted = sum(
                e.days_granted for e in eots
                if e.state in ('granted', 'partial')
            )
            progs = rec.contractor_programme_ids
            rec.programme_count = len(progs)
            approved = progs.filtered(
                lambda p: p.state == 'approved'
            ).sorted('approval_date', reverse=True)
            rec.approved_programme_id = approved[0] if approved else False
            rec.programme_in_delay = any(p.is_in_delay for p in approved)

    # ── SMART BUTTON ACTIONS ──────────────────────────────────────────────────
    def action_open_site_instructions(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Site Instructions — %s') % self.name,
            'res_model': 'salaam.site.instruction',
            'view_mode': 'list,form',
            'domain': [('project_id', '=', self.id)],
            'context': {'default_project_id': self.id},
        }

    def action_open_ncrs(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('NCRs — %s') % self.name,
            'res_model': 'salaam.ncr',
            'view_mode': 'list,form',
            'domain': [('project_id', '=', self.id)],
            'context': {'default_project_id': self.id},
        }

    def action_open_eots(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('EOT Claims — %s') % self.name,
            'res_model': 'salaam.eot.claim',
            'view_mode': 'list,form',
            'domain': [('project_id', '=', self.id)],
            'context': {'default_project_id': self.id},
        }

    def action_open_programmes(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Contractor Programmes — %s') % self.name,
            'res_model': 'salaam.contractor.programme',
            'view_mode': 'list,form',
            'domain': [('project_id', '=', self.id)],
            'context': {'default_project_id': self.id},
        }
