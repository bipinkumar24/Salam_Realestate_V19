# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import ValidationError, UserError
from dateutil.relativedelta import relativedelta


class InvestmentApplication(models.Model):
    _name = 'property.investment.application'
    _description = 'Individual Investment Proposal'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'name'
    _order = 'date_application desc, id desc'

    # ─── Identity & Sequence ────────────────────────────────────────────────
    name = fields.Char(
        string='Application Number',
        default=lambda self: self.env['ir.sequence'].next_by_code(
            'property.investment.application'),
        copy=False,
        readonly=True,
    )
    state = fields.Selection([
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('review', 'Under Review'),
        ('approved', 'Approved'),
        ('conditional', 'Approved with Condition'),
        ('rejected', 'Rejected'),
    ], default='draft', tracking=True, string='Status')

    date_application = fields.Date(
        string='Application Date',
        default=fields.Date.today,
        required=True,
    )
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        default=lambda self: self.env.company.currency_id,
        required=True,
    )
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company,
    )

    # ─── Section 3: Character (5%) — General Information ─────────────────────
    partner_id = fields.Many2one(
        'res.partner', string='Customer Full Name', required=True, tracking=True)
    phone = fields.Char(string='Phone Number', related='partner_id.phone', readonly=False)
    date_of_birth = fields.Date(string='Date of Birth')
    age = fields.Integer(
        string='Age', compute='_compute_age', store=True)
    account_no = fields.Char(string='Account No.')
    date_account_opened = fields.Date(string='Date Account Opened')
    previous_loan_amount = fields.Monetary(string='Previous Loan Amount')
    dependents_count = fields.Integer(string='Number of Dependents')
    account_id_ref = fields.Char(string='Account ID')
    account_statement_balance = fields.Monetary(string='Account Statement Balance')
    avg_balance = fields.Monetary(string='Average Balance')
    existing_monthly_payment = fields.Monetary(string='Existing Monthly Payment')
    marital_status = fields.Selection([
        ('single', 'Single'),
        ('married', 'Married'),
        ('divorced', 'Divorced'),
        ('widowed', 'Widowed'),
    ], string='Marital Status')
    residence_type = fields.Selection([
        ('owned', 'Owned'),
        ('rented', 'Rented'),
        ('family', 'Family'),
    ], string='Residence Type')
    repayment_rate = fields.Float(string='Repayment Rate', digits=(5, 2),
                                   help='e.g. 0.75 = 75%')
    education_level = fields.Selection([
        ('none', 'None'),
        ('primary', 'Primary'),
        ('secondary', 'Secondary'),
        ('diploma', 'Diploma'),
        ('degree', 'Degree'),
        ('postgrad', 'Post-Graduate'),
    ], string='Education Level')
    gender = fields.Selection([
        ('male', 'Male'),
        ('female', 'Female'),
        ('other', 'Other'),
    ], string='Gender')
    financing_type = fields.Selection([
        ('mrbh', 'MRBH'),
        ('murabaha', 'Murabaha'),
        ('ijara', 'Ijara'),
        ('diminishing', 'Diminishing Musharakah'),
        ('conventional', 'Conventional'),
    ], string='Financing Type')

    # ─── Section 4: Condition (5%) — Employment & Business ──────────────────
    employer_name = fields.Char(string='Employer')
    job_title = fields.Char(string='Job Title & Position')
    employment_years = fields.Integer(string='Length of Employment (years)')
    employment_type = fields.Selection([
        ('employee', 'Employed'),
        ('business', 'Business Owner'),
        ('both', 'Both'),
    ], string='Primary Income Source')
    business_name = fields.Char(string='Business Name')
    sector_id = fields.Many2one(
        'property.sector', string='Nature of Business / Sector')
    business_years = fields.Integer(string='No. of Years in Business')
    # branch_id = fields.Many2one('res.branch', string='Branch')  # Uncomment if multi-branch module is installed

    # ─── Section 5: Capital (15%) — Assets ──────────────────────────────────
    asset_cash = fields.Monetary(string='Cash & Equivalents')
    asset_shares = fields.Monetary(string='Business Shares')
    asset_real_estate = fields.Monetary(string='Real Estate')
    asset_personal_biz = fields.Monetary(string='Personal Business')
    asset_house = fields.Monetary(string='House / Residence')
    asset_automobiles = fields.Monetary(string='Automobiles')
    asset_other = fields.Monetary(string='Other Assets')
    total_assets = fields.Monetary(
        string='Total Assets (A)',
        compute='_compute_assets',
        store=True,
    )

    # ─── Section 5: Capital (15%) — Liabilities ─────────────────────────────
    liability_ids = fields.One2many(
        'property.investment.liability', 'application_id', string='Liabilities')
    total_liabilities = fields.Monetary(
        string='Total Liabilities (B)',
        compute='_compute_liabilities',
        store=True,
    )
    total_monthly_liability_payment = fields.Monetary(
        string='Total Monthly Liability Payment',
        compute='_compute_liabilities',
        store=True,
    )
    net_worth = fields.Monetary(
        string='Net Worth (A − B)',
        compute='_compute_net_worth',
        store=True,
    )

    # ─── Section 6: Capacity (50%) — Income ─────────────────────────────────
    income_salary = fields.Monetary(string='Monthly Salary')
    income_commission = fields.Monetary(string='Commissions / Bonus')
    income_business = fields.Monetary(string='Business Income')
    income_rental = fields.Monetary(string='Rental Income')
    income_other = fields.Monetary(string='Other Income')
    total_gross_income = fields.Monetary(
        string='Total Gross Income (I)',
        compute='_compute_gross_income',
        store=True,
    )

    # ─── Section 6: Capacity (50%) — Expenses & DPI ─────────────────────────
    expense_basic_living = fields.Monetary(string='Monthly Basic Living Expenses')
    contingency_rate = fields.Float(
        string='Contingency Rate',
        default=0.20,
        help='0.20 for employees, 0.30 for business owners',
    )
    expense_loan_advance = fields.Monetary(
        string='Advance Loan Payment (FA)',
        compute='_compute_expense_advance',
        store=True,
    )
    total_monthly_expenses = fields.Monetary(
        string='Total Monthly Expenses (ME)',
        compute='_compute_income_expense',
        store=True,
    )
    disposable_personal_income = fields.Monetary(
        string='Disposable Personal Income (DPI)',
        compute='_compute_income_expense',
        store=True,
    )
    contingency_amount = fields.Monetary(
        string='Contingency Amount',
        compute='_compute_income_expense',
        store=True,
    )
    net_disposable_income = fields.Monetary(
        string='Net Disposable Income (NDI)',
        compute='_compute_income_expense',
        store=True,
    )

    # ─── Section 7: Financing Terms & IIR ───────────────────────────────────
    financing_required_amount = fields.Monetary(string='Required Amount (A)')
    profit_rate = fields.Float(
        string='Annual Profit Rate',
        digits=(5, 4),
        help='e.g. 0.0365 = 3.65%',
    )
    advance_payment_pct = fields.Float(
        string='Advance Payment %',
        default=0.30,
        help='e.g. 0.30 = 30%',
    )
    financing_period_months = fields.Integer(
        string='Financing Period (months)',
        default=12,
    )
    advance_payment_amount = fields.Monetary(
        string='Advance Payment Amount (C)',
        compute='_compute_financing',
        store=True,
    )
    profit_amount = fields.Monetary(
        string='Profit Amount (B)',
        compute='_compute_financing',
        store=True,
    )
    total_price = fields.Monetary(
        string='Total Price (A + B − C)',
        compute='_compute_financing',
        store=True,
    )
    monthly_installment = fields.Monetary(
        string='Monthly Installment',
        compute='_compute_financing',
        store=True,
    )
    iir = fields.Float(
        string='IIR (Installment / NDI)',
        compute='_compute_iir',
        store=True,
        digits=(5, 4),
    )
    iir_status = fields.Selection([
        ('green', 'Within Limit (≤35%)'),
        ('amber', 'Caution (35–40%)'),
        ('red', 'Exceeds Limit (>40%)'),
    ], string='IIR Status', compute='_compute_iir', store=True)

    # ─── Section 8: Collateral (25%) ────────────────────────────────────────
    collateral_ids = fields.One2many(
        'property.investment.collateral', 'application_id', string='Collateral Properties')
    total_collateral_market_value = fields.Monetary(
        string='Total Collateral Market Value',
        compute='_compute_collateral_totals',
        store=True,
    )
    total_collateral_adjusted_value = fields.Monetary(
        string='Total Adjusted Collateral Value',
        compute='_compute_collateral_totals',
        store=True,
    )

    # ─── Section 9: Five Cs Scoring ─────────────────────────────────────────
    score_character = fields.Float('Character Score (5%)', digits=(5, 2),
                                    default=1.0,
                                    help='Enter score 0.00 to 1.00 (1.00 = full marks)')
    score_condition = fields.Float('Condition Score (5%)', digits=(5, 2), default=1.0)
    score_capital = fields.Float('Capital Score (15%)', digits=(5, 2), default=1.0)
    score_capacity = fields.Float('Capacity Score (50%)', digits=(5, 2), default=1.0)
    score_collateral = fields.Float('Collateral Score (25%)', digits=(5, 2), default=1.0)
    total_score = fields.Float(
        string='Total Weighted Score',
        compute='_compute_score',
        store=True,
        digits=(5, 4),
    )
    score_decision = fields.Selection([
        ('approved', 'Approved  (score ≥ 80%)'),
        ('conditional', 'Approved with Condition  (70% – 79%)'),
        ('rejected', 'Rejected  (score < 70%)'),
    ], string='Score Recommendation', compute='_compute_score', store=True)

    # ─── Analyst Notes ───────────────────────────────────────────────────────
    analyst_notes = fields.Text(string='Analyst Notes')
    rejection_reason = fields.Text(string='Rejection / Condition Reason')

    # ════════════════════════════════════════════════════════════════════════
    # COMPUTED METHODS
    # ════════════════════════════════════════════════════════════════════════

    @api.depends('date_of_birth', 'date_application')
    def _compute_age(self):
        for rec in self:
            if rec.date_of_birth and rec.date_application:
                delta = relativedelta(rec.date_application, rec.date_of_birth)
                rec.age = delta.years
            else:
                rec.age = 0

    @api.depends(
        'asset_cash', 'asset_shares', 'asset_real_estate',
        'asset_personal_biz', 'asset_house', 'asset_automobiles', 'asset_other',
    )
    def _compute_assets(self):
        for rec in self:
            rec.total_assets = (
                rec.asset_cash + rec.asset_shares +
                rec.asset_real_estate + rec.asset_personal_biz +
                rec.asset_house + rec.asset_automobiles +
                rec.asset_other
            )

    @api.depends('liability_ids.outstanding_balance', 'liability_ids.monthly_payment')
    def _compute_liabilities(self):
        for rec in self:
            rec.total_liabilities = sum(
                rec.liability_ids.mapped('outstanding_balance'))
            rec.total_monthly_liability_payment = sum(
                rec.liability_ids.mapped('monthly_payment'))

    @api.depends('total_assets', 'total_liabilities')
    def _compute_net_worth(self):
        for rec in self:
            rec.net_worth = rec.total_assets - rec.total_liabilities

    @api.depends(
        'income_salary', 'income_commission',
        'income_business', 'income_rental', 'income_other',
    )
    def _compute_gross_income(self):
        for rec in self:
            rec.total_gross_income = (
                rec.income_salary + rec.income_commission +
                rec.income_business + rec.income_rental +
                rec.income_other
            )

    @api.depends('total_monthly_liability_payment')
    def _compute_expense_advance(self):
        for rec in self:
            rec.expense_loan_advance = rec.total_monthly_liability_payment

    @api.depends(
        'expense_basic_living', 'expense_loan_advance',
        'total_gross_income', 'contingency_rate',
    )
    def _compute_income_expense(self):
        for rec in self:
            # ME = basic living + FA
            rec.total_monthly_expenses = (
                rec.expense_basic_living + rec.expense_loan_advance)
            # DPI = Gross Income − FA
            rec.disposable_personal_income = (
                rec.total_gross_income - rec.expense_loan_advance)
            # Contingency = rate × ME
            rec.contingency_amount = (
                rec.contingency_rate * rec.total_monthly_expenses)
            # NDI = DPI − Contingency
            rec.net_disposable_income = (
                rec.disposable_personal_income - rec.contingency_amount)

    @api.depends(
        'financing_required_amount', 'profit_rate',
        'advance_payment_pct', 'financing_period_months',
    )
    def _compute_financing(self):
        for rec in self:
            A = rec.financing_required_amount
            r = rec.profit_rate
            n = rec.financing_period_months
            pct = rec.advance_payment_pct

            # C = Advance payment
            C = A * pct
            rec.advance_payment_amount = C

            # B = Profit on net financed amount: (A − C) × (r × n / 12)
            B = (A - C) * (r * n / 12.0) if n else 0.0
            rec.profit_amount = B

            # Total Price = (A − C) + B
            rec.total_price = (A - C) + B

            # Monthly Installment = Total Price / n
            rec.monthly_installment = rec.total_price / n if n else 0.0

    @api.depends('monthly_installment', 'net_disposable_income')
    def _compute_iir(self):
        for rec in self:
            if rec.net_disposable_income:
                rec.iir = rec.monthly_installment / rec.net_disposable_income
            else:
                rec.iir = 0.0
            # Color-coded status
            if rec.iir <= 0.35:
                rec.iir_status = 'green'
            elif rec.iir <= 0.40:
                rec.iir_status = 'amber'
            else:
                rec.iir_status = 'red'

    @api.depends('collateral_ids.total_market_value', 'collateral_ids.adjusted_value')
    def _compute_collateral_totals(self):
        for rec in self:
            rec.total_collateral_market_value = sum(
                rec.collateral_ids.mapped('total_market_value'))
            rec.total_collateral_adjusted_value = sum(
                rec.collateral_ids.mapped('adjusted_value'))

    @api.depends(
        'score_character', 'score_condition', 'score_capital',
        'score_capacity', 'score_collateral',
    )
    def _compute_score(self):
        for rec in self:
            rec.total_score = (
                rec.score_character * 0.05 +
                rec.score_condition * 0.05 +
                rec.score_capital * 0.15 +
                rec.score_capacity * 0.50 +
                rec.score_collateral * 0.25
            )
            # ≥ 80% → Approved
            if rec.total_score >= 0.80:
                rec.score_decision = 'approved'
            # 70% – 79% → Approved with Condition
            elif rec.total_score >= 0.70:
                rec.score_decision = 'conditional'
            # < 70% → Rejected
            else:
                rec.score_decision = 'rejected'

            # Sync state to match score_decision whenever the record
            # is already in a decision stage (approved/conditional/rejected)
            if rec.state in ('approved', 'conditional', 'rejected'):
                rec.state = rec.score_decision

    # ════════════════════════════════════════════════════════════════════════
    # CONSTRAINTS
    # ════════════════════════════════════════════════════════════════════════

    @api.constrains('iir', 'state')
    def _check_iir_limit(self):
        for rec in self:
            if rec.state == 'approved' and rec.iir > 0.40:
                raise ValidationError(
                    'Cannot approve: Installment-to-Income Ratio '
                    f'({rec.iir:.1%}) exceeds the maximum of 40%. '
                    'Review the financing terms or applicant income.'
                )

    @api.constrains('score_character', 'score_condition', 'score_capital',
                    'score_capacity', 'score_collateral')
    def _check_scores(self):
        for rec in self:
            for fname in ['score_character', 'score_condition', 'score_capital',
                          'score_capacity', 'score_collateral']:
                val = getattr(rec, fname)
                if not (0.0 <= val <= 1.0):
                    raise ValidationError(
                        f'Score values must be between 0.00 and 1.00 '
                        f'(field: {fname}).')

    # ════════════════════════════════════════════════════════════════════════
    # ONCHANGE
    # ════════════════════════════════════════════════════════════════════════

    @api.onchange('employment_type')
    def _onchange_employment_type(self):
        if self.employment_type == 'employee':
            self.contingency_rate = 0.20
        elif self.employment_type == 'business':
            self.contingency_rate = 0.30
        elif self.employment_type == 'both':
            # Use the higher (conservative) rate
            self.contingency_rate = 0.30

    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        if self.partner_id:
            self.phone = self.partner_id.phone

    # ════════════════════════════════════════════════════════════════════════
    # WORKFLOW ACTIONS
    # ════════════════════════════════════════════════════════════════════════

    def action_submit(self):
        for rec in self:
            rec.state = 'submitted'
            rec.message_post(body='Application submitted for review.')
        return True

    def action_review(self):
        for rec in self:
            rec.state = 'review'
            rec.message_post(body='Application is now under review.')
        return True

    def write(self, vals):
        """When score fields change, recompute and post a chatter note
        if the state changes as a result."""
        score_fields = {
            'score_character', 'score_condition', 'score_capital',
            'score_capacity', 'score_collateral',
        }
        old_states = {rec.id: rec.state for rec in self}             if score_fields & set(vals) else {}
        res = super().write(vals)
        if old_states:
            for rec in self:
                new_state = rec.state
                if old_states.get(rec.id) != new_state:
                    state_labels = {
                        'approved':    'Approved  (score ≥ 80%)',
                        'conditional': 'Approved with Condition  (70%–79%)',
                        'rejected':    'Rejected  (score < 70%)',
                    }
                    rec.message_post(
                        body='Status automatically updated to <b>%s</b> '
                             'based on Five Cs score of <b>%.1f%%</b>.' % (
                            state_labels.get(new_state, new_state),
                            rec.total_score * 100,
                        ),
                        subtype_xmlid='mail.mt_note',
                    )
        return res

    def action_approve(self):
        for rec in self:
            if rec.iir > 0.40:
                raise UserError(
                    f'IIR is {rec.iir:.1%} which exceeds the 40% maximum. '
                    'Cannot approve this application.')
            rec.state = 'approved'
            rec.message_post(body='Application has been APPROVED.')
        return True

    def action_conditional(self):
        for rec in self:
            rec.state = 'conditional'
            rec.message_post(body='Application approved WITH CONDITIONS.')
        return True

    def action_reject(self):
        for rec in self:
            rec.state = 'rejected'
            rec.message_post(body='Application has been REJECTED.')
        return True

    def action_reset_draft(self):
        for rec in self:
            rec.state = 'draft'
            rec.message_post(body='Application reset to Draft.')
        return True
