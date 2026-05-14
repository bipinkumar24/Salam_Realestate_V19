# -*- coding: utf-8 -*-
from odoo import _, fields, models
from odoo.exceptions import UserError


class CrmLead(models.Model):
    _inherit = 'crm.lead'

    buruuj_tender_id = fields.Many2one(
        'buruuj.tender', string='Tender Estimate',
        copy=False, ondelete='set null',
        help='BOQ-based tender record created from this opportunity.',
    )
    has_buruuj_tender = fields.Boolean(
        compute='_compute_has_buruuj_tender', store=True,
    )

    def _compute_has_buruuj_tender(self):
        for rec in self:
            rec.has_buruuj_tender = bool(rec.buruuj_tender_id)

    def action_create_buruuj_tender(self):
        self.ensure_one()
        if self.buruuj_tender_id:
            raise UserError(_('A tender estimate already exists for this opportunity.'))
        if not self.is_tender:
            raise UserError(_('This opportunity is not flagged as a tender.'))
        if self.tender_state not in ('kickoff', 'capture', 'bid_decision'):
            raise UserError(_(
                'Tender estimate can only be created from Capture, Bid Decision, '
                'or Kickoff stage.'
            ))
        if not self.client_id:
            raise UserError(_('Set the issuing entity (client) before converting.'))

        # Ensure the partner is flagged as a client for buruuj_tendering's domain.
        if not self.client_id.is_client:
            self.client_id.is_client = True

        tender_vals = {
            'title': self.name or _('New Tender'),
            'client_id': self.client_id.id,
            'submission_deadline': self.submission_deadline,
            'estimated_value': self.tender_value_estimate,
            'currency_id': self.company_currency.id,
            'estimator_id': self.user_id.id or self.env.user.id,
            'company_id': self.company_id.id,
            'crm_lead_id': self.id,
        }
        if self.partner_id and self.partner_id.city:
            tender_vals['location'] = self.partner_id.city
        tender = self.env['buruuj.tender'].create(tender_vals)
        self.buruuj_tender_id = tender.id

        return {
            'type': 'ir.actions.act_window',
            'name': _('Tender Estimate'),
            'res_model': 'buruuj.tender',
            'res_id': tender.id,
            'view_mode': 'form',
        }

    def action_open_buruuj_tender(self):
        self.ensure_one()
        if not self.buruuj_tender_id:
            raise UserError(_('No tender estimate linked to this opportunity.'))
        return {
            'type': 'ir.actions.act_window',
            'name': _('Tender Estimate'),
            'res_model': 'buruuj.tender',
            'res_id': self.buruuj_tender_id.id,
            'view_mode': 'form',
        }
