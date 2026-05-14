# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError


# ══════════════════════════════════════════════════════════════════════════════
#  EXTENSION: bre.customer.application  →  link to property.investment.application
# ══════════════════════════════════════════════════════════════════════════════

class CustomerApplicationAppraisalBridge(models.Model):
    """
    Extends the BRE Customer Application with a bridge to the
    Property Investment Appraisal (Five Cs) module.

    Design decisions:
    - One BRE application can have ONE linked appraisal record.
    - Creating an appraisal auto-populates it from the BRE application data.
    - Appraisal state changes are reflected back on the BRE application.
    - The bank officer can navigate directly between both records.
    """
    _inherit = 'bre.customer.application'

    # ── Link ──────────────────────────────────────────────────────────────────
    appraisal_id = fields.Many2one(
        'property.investment.application',
        string='Investment Appraisal',
        ondelete='set null',
        tracking=True,
        copy=False,
    )
    appraisal_state = fields.Selection(
        related='appraisal_id.state',
        string='Appraisal Status',
        store=True,
    )
    appraisal_total_score = fields.Float(
        related='appraisal_id.total_score',
        string='Five Cs Score (%)',
        store=True,
    )
    appraisal_score_decision = fields.Selection(
        related='appraisal_id.score_decision',
        string='Score Recommendation',
        store=True,
    )
    appraisal_iir = fields.Float(
        related='appraisal_id.iir',
        string='IIR',
        store=True,
    )
    appraisal_iir_status = fields.Selection(
        related='appraisal_id.iir_status',
        string='IIR Status',
        store=True,
    )
    appraisal_monthly_installment = fields.Monetary(
        related='appraisal_id.monthly_installment',
        string='Appraisal Monthly Installment',
        currency_field='currency_id',
        store=True,
    )
    appraisal_net_disposable_income = fields.Monetary(
        related='appraisal_id.net_disposable_income',
        string='Net Disposable Income (NDI)',
        currency_field='currency_id',
        store=True,
    )
    appraisal_net_worth = fields.Monetary(
        related='appraisal_id.net_worth',
        string='Net Worth (Assets − Liabilities)',
        currency_field='currency_id',
        store=True,
    )
    appraisal_total_collateral = fields.Monetary(
        related='appraisal_id.total_collateral_adjusted_value',
        string='Adjusted Collateral Value',
        currency_field='currency_id',
        store=True,
    )
    has_appraisal = fields.Boolean(
        string='Has Appraisal',
        compute='_compute_has_appraisal',
        store=True,
    )

    @api.depends('appraisal_id')
    def _compute_has_appraisal(self):
        for rec in self:
            rec.has_appraisal = bool(rec.appraisal_id)

    # ── Actions ───────────────────────────────────────────────────────────────

    def action_create_appraisal(self):
        """
        Create a new property.investment.application pre-populated from
        the BRE customer application data, then open it in a form view.
        """
        self.ensure_one()
        if self.appraisal_id:
            raise UserError(_(
                'An appraisal already exists for this application: %s'
            ) % self.appraisal_id.name)

        if not self.partner_id:
            raise UserError(_(
                'Please select a Customer (CRM contact) before creating an appraisal.'
            ))

        # Map financing type between the two modules
        financing_map = {
            'murabaha':               'murabaha',
            'ijara':                  'ijara',
            'diminishing_musharaka':  'diminishing',
            'conventional':           'conventional',
            'cash':                   'conventional',
        }
        # Map employment status
        employment_map = {
            'employed':       'employee',
            'self_employed':  'business',
            'business_owner': 'business',
            'retired':        'employee',
            'unemployed':     'employee',
        }

        # Build appraisal values from BRE application data
        appraisal_vals = {
            # Identity — use the already-linked CRM partner directly
            'partner_id':               self.partner_id.id,
            'date_application':         self.application_date or fields.Date.today(),
            'currency_id':              self.currency_id.id,

            # Character — personal profile
            'date_of_birth':            self.date_of_birth,
            'gender':                   self.gender,
            'marital_status':           self.marital_status,
            'dependents_count':         self.dependents_count,
            'phone':                    self.mobile,

            # Condition — employment
            'employer_name':            self.employer_name,
            'job_title':                self.job_title,
            'employment_years':         self.years_employed,
            'employment_type':          employment_map.get(self.employment_status, 'employee'),

            # Capacity — income
            'income_salary':            self.monthly_income,
            'income_other':             self.other_income,
            'expense_basic_living':     self.monthly_obligations,

            # Financing terms
            'financing_type':           financing_map.get(self.financing_type, 'murabaha'),
            'financing_required_amount': self.financing_amount,
            'financing_period_months':  self.tenure_months or 240,
            'advance_payment_pct':      (self.down_payment / self.property_price)
                                        if self.property_price else 0.30,
        }

        appraisal = self.env['property.investment.application'].create(appraisal_vals)
        self.appraisal_id = appraisal.id

        self.message_post(
            body=_('Investment Appraisal <a href="/web#id=%d&model=property.investment.application">'
                   '%s</a> created and linked to this application.') % (
                appraisal.id, appraisal.name),
            subtype_xmlid='mail.mt_note',
        )

        return {
            'type': 'ir.actions.act_window',
            'name': _('Investment Appraisal'),
            'res_model': 'property.investment.application',
            'res_id': appraisal.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_open_appraisal(self):
        """Navigate to the linked appraisal record."""
        self.ensure_one()
        if not self.appraisal_id:
            raise UserError(_('No appraisal linked. Please create one first.'))
        return {
            'type': 'ir.actions.act_window',
            'name': _('Investment Appraisal'),
            'res_model': 'property.investment.application',
            'res_id': self.appraisal_id.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_sync_from_appraisal(self):
        """
        Pull approved financing figures back from the appraisal into the
        BRE application — useful when the credit team adjusts terms.
        """
        self.ensure_one()
        if not self.appraisal_id:
            raise UserError(_('No appraisal linked to this application.'))

        ap = self.appraisal_id
        sync_vals = {}

        # Pull back income/financial data
        if ap.total_gross_income:
            sync_vals['monthly_income'] = ap.income_salary
            sync_vals['other_income'] = (
                ap.income_commission + ap.income_business +
                ap.income_rental + ap.income_other
            )
        if ap.total_monthly_liability_payment:
            sync_vals['monthly_obligations'] = ap.total_monthly_liability_payment

        # Pull financing figures if appraisal is approved/conditional
        if ap.state in ('approved', 'conditional'):
            sync_vals['financing_amount'] = ap.financing_required_amount
            sync_vals['tenure_months'] = ap.financing_period_months
            sync_vals['expected_monthly_payment'] = ap.monthly_installment
            if ap.advance_payment_amount:
                sync_vals['down_payment'] = ap.advance_payment_amount

        if sync_vals:
            self.write(sync_vals)
            self.message_post(
                body=_('Financial data synced from appraisal %s.') % ap.name,
                subtype_xmlid='mail.mt_note',
            )
        return True

    # ── Appraisal state → BRE bank_status sync ────────────────────────────────
    def _sync_appraisal_decision_to_bre(self):
        """
        Called when the linked appraisal changes state. Maps appraisal
        state back to BRE bank_status so both records stay consistent.
        """
        state_map = {
            'approved':    'approved',
            'conditional': 'approved',
            'rejected':    'rejected',
            'review':      'under_review',
            'submitted':   'pending',
        }
        for rec in self:
            if rec.appraisal_id:
                new_status = state_map.get(rec.appraisal_id.state)
                if new_status and rec.bank_status != new_status:
                    rec.bank_status = new_status
                    rec.message_post(
                        body=_('Bank status updated to <b>%s</b> based on '
                               'appraisal decision (%s).') % (
                            new_status, rec.appraisal_id.state),
                        subtype_xmlid='mail.mt_note',
                    )


# ══════════════════════════════════════════════════════════════════════════════
#  EXTENSION: property.investment.application  →  back-link to BRE application
# ══════════════════════════════════════════════════════════════════════════════

class InvestmentApplicationBREBridge(models.Model):
    """
    Extends the Investment Appraisal with a back-reference to the originating
    BRE Customer Application, plus a hook that syncs state changes back.
    """
    _inherit = 'property.investment.application'

    # Back-reference (computed — not stored to avoid circular FK)
    bre_application_id = fields.Many2one(
        'bre.customer.application',
        string='BRE Application',
        compute='_compute_bre_application',
        store=True,
    )
    bre_application_ref = fields.Char(
        string='BRE Application Ref',
        compute='_compute_bre_application',
        store=False,
    )
    bre_property_name = fields.Char(
        string='Linked Property',
        compute='_compute_bre_application',
        store=False,
    )

    def _compute_bre_application(self):
        BRE = self.env['bre.customer.application']
        for rec in self:
            app = BRE.search([('appraisal_id', '=', rec.id)], limit=1)
            rec.bre_application_id  = app.id if app else False
            rec.bre_application_ref = app.name if app else ''
            rec.bre_property_name   = app.property_id.name if app and app.property_id else ''

    def action_open_bre_application(self):
        """Navigate back to the originating BRE application."""
        self.ensure_one()
        app = self.env['bre.customer.application'].search(
            [('appraisal_id', '=', self.id)], limit=1)
        if not app:
            raise UserError(_('No BRE application is linked to this appraisal.'))
        return {
            'type': 'ir.actions.act_window',
            'name': _('Customer Application'),
            'res_model': 'bre.customer.application',
            'res_id': app.id,
            'view_mode': 'form',
            'target': 'current',
        }

    # ── Sync state changes back to BRE ────────────────────────────────────────
    def write(self, vals):
        res = super().write(vals)
        if 'state' in vals:
            bre_apps = self.env['bre.customer.application'].search(
                [('appraisal_id', 'in', self.ids)])
            bre_apps._sync_appraisal_decision_to_bre()
        return res

    def action_approve(self):
        res = super().action_approve()
        self._notify_bre_on_decision('approved')
        return res

    def action_conditional(self):
        res = super().action_conditional()
        self._notify_bre_on_decision('conditional')
        return res

    def action_reject(self):
        res = super().action_reject()
        self._notify_bre_on_decision('rejected')
        return res

    def _notify_bre_on_decision(self, decision):
        """Post a message on the linked BRE application when appraisal decides."""
        label_map = {
            'approved':    '✅ Approved',
            'conditional': '⚠️ Conditionally Approved',
            'rejected':    '❌ Rejected',
        }
        for rec in self:
            app = self.env['bre.customer.application'].search(
                [('appraisal_id', '=', rec.id)], limit=1)
            if app:
                app.message_post(
                    body=_(
                        'Investment Appraisal <b>%s</b> decision: <b>%s</b><br/>'
                        'Five Cs Score: <b>%.1f%%</b> | IIR: <b>%.1f%%</b>'
                    ) % (
                        rec.name,
                        label_map.get(decision, decision),
                        rec.total_score * 100,
                        rec.iir * 100,
                    ),
                    subtype_xmlid='mail.mt_comment',
                )


# ══════════════════════════════════════════════════════════════════════════════
#  EXTENSION: bre.financing.request  →  pull IIR / score from appraisal
# ══════════════════════════════════════════════════════════════════════════════

class FinancingRequestAppraisalBridge(models.Model):
    _inherit = 'bre.financing.request'

    appraisal_score = fields.Float(
        string='Five Cs Score (%)',
        related='application_id.appraisal_total_score',
        store=True,
    )
    appraisal_iir = fields.Float(
        string='IIR',
        related='application_id.appraisal_iir',
        store=True,
    )
    appraisal_iir_status = fields.Selection(
        related='application_id.appraisal_iir_status',
        string='IIR Status',
        store=True,
    )
    appraisal_decision = fields.Selection(
        related='application_id.appraisal_score_decision',
        string='Appraisal Recommendation',
        store=True,
    )
    appraisal_net_worth = fields.Monetary(
        related='application_id.appraisal_net_worth',
        string='Net Worth',
        currency_field='currency_id',
        store=True,
    )
    appraisal_collateral = fields.Monetary(
        related='application_id.appraisal_total_collateral',
        string='Adjusted Collateral',
        currency_field='currency_id',
        store=True,
    )
