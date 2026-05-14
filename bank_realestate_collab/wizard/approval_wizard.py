# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class ApprovalWizard(models.TransientModel):
    _name = 'bre.approval.wizard'
    _description = 'Application Approval Wizard'

    application_id = fields.Many2one('bre.customer.application', string='Application',
                                     required=True)
    approved_amount = fields.Monetary(string='Approved Amount', currency_field='currency_id',
                                      required=True)
    approved_tenure = fields.Integer(string='Approved Tenure (months)', required=True)
    approved_rate = fields.Float(string='Profit/Interest Rate (% p.a.)', required=True)
    conditions = fields.Text(string='Approval Conditions')
    offer_expiry_date = fields.Date(string='Offer Expiry Date')
    bank_notes = fields.Text(string='Bank Notes')
    currency_id = fields.Many2one('res.currency', string='Currency',
                                  default=lambda self: self.env.company.currency_id)

    @api.constrains('approved_amount')
    def _check_amount(self):
        for rec in self:
            if rec.approved_amount <= 0:
                raise ValidationError(_('Approved amount must be positive.'))

    def action_confirm_approval(self):
        self.ensure_one()
        app = self.application_id
        app.write({
            'bank_status': 'approved',
            'approved_amount': self.approved_amount,
            'approved_tenure': self.approved_tenure,
            'approved_rate': self.approved_rate,
            'conditions': self.conditions,
            'bank_notes': self.bank_notes,
            'decision_date': fields.Datetime.now(),
            'bank_officer_id': self.env.user.id,
        })
        # Update related financing requests
        app.financing_request_ids.filtered(
            lambda r: r.status == 'under_review'
        ).write({
            'status': 'approved',
            'approved_amount': self.approved_amount,
            'approved_tenure': self.approved_tenure,
            'profit_rate': self.approved_rate,
            'conditions': self.conditions,
            'decision_date': fields.Datetime.now(),
            'offer_expiry_date': self.offer_expiry_date,
        })
        app.message_post(
            body=_('✅ Application APPROVED by %s. Amount: %s | Tenure: %s months | Rate: %s%%') % (
                self.env.user.name, self.approved_amount, self.approved_tenure, self.approved_rate
            ),
            subtype_xmlid='mail.mt_comment'
        )
        return {'type': 'ir.actions.act_window_close'}


class RejectionWizard(models.TransientModel):
    _name = 'bre.rejection.wizard'
    _description = 'Application Rejection Wizard'

    application_id = fields.Many2one('bre.customer.application', string='Application',
                                     required=True)
    rejection_reason = fields.Text(string='Rejection Reason', required=True)
    rejection_category = fields.Selection([
        ('insufficient_income', 'Insufficient Income'),
        ('high_dbr', 'High Debt Burden Ratio'),
        ('poor_credit', 'Poor Credit History'),
        ('incomplete_docs', 'Incomplete Documents'),
        ('property_issues', 'Property Related Issues'),
        ('policy', 'Bank Policy'),
        ('other', 'Other'),
    ], string='Rejection Category', required=True)
    bank_notes = fields.Text(string='Additional Notes')
    can_reapply = fields.Boolean(string='Eligible to Reapply', default=True)
    reapply_after_days = fields.Integer(string='Reapply After (days)', default=90)

    def action_confirm_rejection(self):
        self.ensure_one()
        app = self.application_id
        full_reason = f"[{dict(self._fields['rejection_category'].selection).get(self.rejection_category)}] {self.rejection_reason}"
        app.write({
            'bank_status': 'rejected',
            'rejection_reason': full_reason,
            'bank_notes': self.bank_notes,
            'decision_date': fields.Datetime.now(),
            'bank_officer_id': self.env.user.id,
        })
        app.financing_request_ids.filtered(
            lambda r: r.status in ('submitted', 'under_review')
        ).write({
            'status': 'rejected',
            'rejection_reason': full_reason,
            'decision_date': fields.Datetime.now(),
        })
        app.message_post(
            body=_('❌ Application REJECTED by %s.\nReason: %s') % (
                self.env.user.name, full_reason
            ),
            subtype_xmlid='mail.mt_comment'
        )
        return {'type': 'ir.actions.act_window_close'}
