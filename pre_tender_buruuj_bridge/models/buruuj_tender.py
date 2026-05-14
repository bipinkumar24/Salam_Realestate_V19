# -*- coding: utf-8 -*-
from odoo import _, fields, models


class BuruujTender(models.Model):
    _inherit = 'buruuj.tender'

    crm_lead_id = fields.Many2one(
        'crm.lead', string='Pre-Tender Opportunity',
        copy=False, ondelete='set null', index=True,
        help='Originating opportunity in the pre-tender pipeline.',
    )
    pretender_compliance_progress = fields.Float(
        related='crm_lead_id.compliance_progress', readonly=True,
    )
    pretender_tier1_complete = fields.Boolean(
        related='crm_lead_id.tier1_complete', readonly=True,
    )
    pretender_high_risk_count = fields.Integer(
        related='crm_lead_id.high_risk_count', readonly=True,
    )

    def action_open_pretender(self):
        self.ensure_one()
        if not self.crm_lead_id:
            return False
        return {
            'type': 'ir.actions.act_window',
            'name': _('Pre-Tender Opportunity'),
            'res_model': 'crm.lead',
            'res_id': self.crm_lead_id.id,
            'view_mode': 'form',
        }

    def _mirror_state_to_lead(self, target_tender_state):
        for rec in self:
            if rec.crm_lead_id and rec.crm_lead_id.tender_state != target_tender_state:
                rec.crm_lead_id.with_context(skip_pretender_gate=True).write({
                    'tender_state': target_tender_state,
                })

    def action_submit(self):
        res = super().action_submit()
        self._mirror_state_to_lead('submitted')
        return res

    def action_won(self):
        res = super().action_won()
        for rec in self:
            if rec.crm_lead_id and not rec.crm_lead_id.tier1_complete:
                # Tier 1 gate: log a warning activity but allow the tender to win
                # (BOQ-side win can outpace pre-tender housekeeping).
                rec.crm_lead_id.activity_schedule(
                    'mail.mail_activity_data_warning',
                    summary=_('Tender won with incomplete Tier 1 housekeeping'),
                    note=_('Close out compliance, survey and bid-decision items for audit.'),
                )
        self._mirror_state_to_lead('won')
        return res

    def action_lost(self):
        res = super().action_lost()
        self._mirror_state_to_lead('lost')
        return res

    def action_cancel(self):
        res = super().action_cancel()
        self._mirror_state_to_lead('withdrawn')
        return res
