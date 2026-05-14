# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class FinancingRequest(models.Model):
    _name = 'bre.financing.request'
    _description = 'Bank Financing Request'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    name = fields.Char(string='Request Reference', readonly=True, default='New', copy=False)
    application_id = fields.Many2one('bre.customer.application', string='Customer Application',
                                     required=True, ondelete='cascade', tracking=True)
    agent_id = fields.Many2one('res.users', string='Submitted By', tracking=True)
    bank_officer_id = fields.Many2one('res.users', string='Bank Officer', tracking=True)

    # Financing Details
    financing_type = fields.Selection([
        ('murabaha', 'Murabaha (Islamic)'),
        ('ijara', 'Ijara (Islamic Lease)'),
        ('diminishing_musharaka', 'Diminishing Musharaka'),
        ('conventional', 'Conventional Mortgage'),
        ('cash', 'Cash Purchase'),
    ], string='Financing Type', required=True, tracking=True)

    requested_amount = fields.Monetary(string='Requested Amount', currency_field='currency_id',
                                       required=True, tracking=True)
    requested_tenure = fields.Integer(string='Requested Tenure (months)', default=240)
    currency_id = fields.Many2one('res.currency', string='Currency',
                                  default=lambda self: self.env.company.currency_id)

    # Bank Decision
    status = fields.Selection([
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('under_review', 'Under Review'),
        ('approved', 'Approved'),
        ('conditional', 'Conditionally Approved'),
        ('rejected', 'Rejected'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='draft', tracking=True)

    approved_amount = fields.Monetary(string='Approved Amount', currency_field='currency_id',
                                      tracking=True)
    approved_tenure = fields.Integer(string='Approved Tenure (months)')
    profit_rate = fields.Float(string='Profit Rate (% p.a.)', tracking=True)
    monthly_installment = fields.Monetary(string='Monthly Installment',
                                          currency_field='currency_id',
                                          compute='_compute_monthly_installment', store=True)
    total_cost = fields.Monetary(string='Total Cost of Financing', currency_field='currency_id',
                                 compute='_compute_total_cost', store=True)
    processing_fee = fields.Monetary(string='Processing Fee', currency_field='currency_id')

    # Conditions & Notes
    conditions = fields.Text(string='Approval Conditions')
    rejection_reason = fields.Text(string='Rejection Reason')
    bank_remarks = fields.Text(string='Bank Remarks')

    # Sharia
    is_sharia_compliant = fields.Boolean(string='Sharia Compliant', default=True)
    sharia_board_approval = fields.Boolean(string='Sharia Board Approved')
    sharia_approval_ref = fields.Char(string='Sharia Approval Reference')

    # Dates
    submission_date = fields.Datetime(string='Submission Date')
    review_date = fields.Datetime(string='Review Date')
    decision_date = fields.Datetime(string='Decision Date')
    offer_expiry_date = fields.Date(string='Offer Expiry Date')

    # Customer mirror fields (for quick bank access)
    customer_name = fields.Char(related='application_id.customer_name', string='Customer Name', store=True)
    property_ref = fields.Char(related='application_id.property_id.property_seq', string='Property Code', store=True)
    monthly_income = fields.Monetary(related='application_id.total_monthly_income',
                                     string='Monthly Income', currency_field='currency_id', store=True)
    debt_burden_ratio = fields.Float(related='application_id.debt_burden_ratio', string='DBR %', store=True)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('bre.financing.request') or 'New'
        return super().create(vals_list)

    @api.depends('approved_amount', 'profit_rate', 'approved_tenure')
    def _compute_monthly_installment(self):
        for rec in self:
            if rec.approved_amount and rec.profit_rate and rec.approved_tenure:
                monthly_rate = rec.profit_rate / 100 / 12
                n = rec.approved_tenure
                if monthly_rate > 0:
                    rec.monthly_installment = rec.approved_amount * (
                        monthly_rate * (1 + monthly_rate) ** n
                    ) / ((1 + monthly_rate) ** n - 1)
                else:
                    rec.monthly_installment = rec.approved_amount / n if n else 0
            else:
                rec.monthly_installment = 0

    @api.depends('monthly_installment', 'approved_tenure')
    def _compute_total_cost(self):
        for rec in self:
            rec.total_cost = rec.monthly_installment * rec.approved_tenure

    def action_submit(self):
        self.write({'status': 'submitted', 'submission_date': fields.Datetime.now()})
        self.message_post(body=_('Financing request submitted.'), subtype_xmlid='mail.mt_note')

    def action_start_review(self):
        self.write({
            'status': 'under_review',
            'review_date': fields.Datetime.now(),
            'bank_officer_id': self.env.user.id,
        })

    def action_approve(self):
        if not self.approved_amount:
            raise ValidationError(_('Please set the approved amount before approving.'))
        self.write({'status': 'approved', 'decision_date': fields.Datetime.now()})
        self.application_id.write({
            'bank_status': 'approved',
            'approved_amount': self.approved_amount,
            'approved_tenure': self.approved_tenure,
            'approved_rate': self.profit_rate,
            'decision_date': fields.Datetime.now(),
        })
        self.message_post(body=_('Financing request approved.'), subtype_xmlid='mail.mt_note')

    def action_reject(self):
        self.write({'status': 'rejected', 'decision_date': fields.Datetime.now()})
        self.application_id.write({'bank_status': 'rejected'})

    def action_conditional_approve(self):
        self.write({'status': 'conditional', 'decision_date': fields.Datetime.now()})


class DocumentType(models.Model):
    _name = 'bre.document.type'
    _description = 'Required Document Type'

    name = fields.Char(string='Document Type', required=True, translate=True)
    code = fields.Char(string='Code')
    description = fields.Text(string='Description')
    is_mandatory = fields.Boolean(string='Mandatory', default=True)
    applicable_for = fields.Selection([
        ('all', 'All Applicants'),
        ('employed', 'Employed'),
        ('self_employed', 'Self-Employed / Business Owner'),
        ('sharia', 'Sharia Financing'),
    ], string='Applicable For', default='all')
    active = fields.Boolean(default=True)
