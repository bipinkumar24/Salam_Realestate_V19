# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
from datetime import date


class CustomerApplication(models.Model):
    _name = 'bre.customer.application'
    _description = 'Customer Onboarding Application'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    # ─────────────────────────────────────────────
    # Basic Info
    # ─────────────────────────────────────────────
    name = fields.Char(string='Application Reference', readonly=True, default='New', copy=False)
    agent_id = fields.Many2one('res.users', string='Real Estate Agent', required=True,
                               default=lambda self: self.env.user, tracking=True)
    bank_officer_id = fields.Many2one('res.users', string='Assigned Bank Officer', tracking=True)

    # ─────────────────────────────────────────────
    # Stage / Status
    # ─────────────────────────────────────────────
    stage_id = fields.Many2one('bre.application.stage', string='Stage',
                               default=lambda self: self._default_stage(),
                               group_expand='_read_group_stage_ids', tracking=True)

    kanban_state = fields.Selection([
        ('normal', 'In Progress'),
        ('done', 'Ready for Next Stage'),
        ('blocked', 'Blocked'),
    ], string='Kanban State', default='normal', tracking=True)

    bank_status = fields.Selection([
        ('not_submitted', 'Not Submitted'),
        ('pending', 'Pending Review'),
        ('under_review', 'Under Review'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('on_hold', 'On Hold'),
    ], string='Bank Status', default='not_submitted', tracking=True)

    priority = fields.Selection([
        ('0', 'Normal'),
        ('1', 'Medium'),
        ('2', 'High'),
        ('3', 'Urgent'),
    ], string='Priority', default='0')

    # ─────────────────────────────────────────────
    # Customer Personal Details
    # ─────────────────────────────────────────────
    partner_id = fields.Many2one(
        'res.partner',
        string='Customer',
        required=True,
        tracking=True,
        help='Select an existing contact from CRM or create a new one.',
    )
    # Convenience char — kept so existing references (reports, related fields)
    # continue to work without changes.
    customer_name = fields.Char(
        string='Full Name',
        related='partner_id.name',
        store=True,
        readonly=False,
    )
    customer_name_ar = fields.Char(string='Full Name (Arabic)')
    date_of_birth = fields.Date(string='Date of Birth', required=True)
    age = fields.Integer(string='Age', compute='_compute_age', store=True)
    gender = fields.Selection([
        ('male', 'Male'),
        ('female', 'Female'),
    ], string='Gender', required=True)
    nationality_id = fields.Many2one('res.country', string='Nationality', required=True)
    marital_status = fields.Selection([
        ('single', 'Single'),
        ('married', 'Married'),
        ('divorced', 'Divorced'),
        ('widowed', 'Widowed'),
    ], string='Marital Status')
    dependents_count = fields.Integer(string='Number of Dependents')

    # Contact — auto-filled from partner but editable
    email = fields.Char(string='Email', required=True)
    mobile = fields.Char(string='Mobile', required=True)
    phone = fields.Char(string='Phone')
    address = fields.Text(string='Residential Address')
    city = fields.Char(string='City')
    country_id = fields.Many2one('res.country', string='Country')

    # ─────────────────────────────────────────────
    # CRM / Prioritization Link
    # ─────────────────────────────────────────────
    crm_lead_id = fields.Many2one(
        'crm.lead',
        string='CRM Opportunity',
        tracking=True,
        help='The CRM opportunity linked to this customer. '
             'Auto-detected when a partner is selected.',
    )
    prioritization_id = fields.Many2one(
        'unit.prioritization',
        string='Prioritization Record',
        tracking=True,
        help='Auto-filled from the CRM opportunity linked to this customer.',
    )
    prioritization_number = fields.Char(
        string='Prioritization Number',
        related='prioritization_id.prioritization_number',
        store=True,
        readonly=True,
    )
    prioritization_file_number = fields.Char(
        string='File Number',
        related='prioritization_id.file_number',
        store=True,
        readonly=True,
    )
    prioritization_description = fields.Text(
        string='Prioritization Description',
        related='prioritization_id.description',
        store=True,
        readonly=True,
    )

    def _find_crm_lead(self, partner):
        """
        Find the most relevant open CRM lead/opportunity for a given partner.
        Returns the newest open opportunity, falling back to any lead.
        """
        Lead = self.env['crm.lead']
        # 1. Open opportunity for this partner
        lead = Lead.search([
            ('partner_id', '=', partner.id),
            ('type', '=', 'opportunity'),
            ('active', '=', True),
        ], order='create_date desc', limit=1)
        if not lead:
            # 2. Any lead (open or closed) for this partner
            lead = Lead.search([
                ('partner_id', '=', partner.id),
            ], order='create_date desc', limit=1)
        return lead

    def _find_prioritization(self, lead):
        """
        Find the unit.prioritization record linked to a crm.lead.
        Uses opportunity_id as confirmed by the unit.prioritization model.
        """
        if not lead:
            return self.env['unit.prioritization'].browse()
        return self.env['unit.prioritization'].search(
            [('opportunity_id', '=', lead.id)], limit=1
        )

    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        """
        Auto-populate contact fields and prioritization info
        from the selected CRM partner.
        """
        if not self.partner_id:
            self.crm_lead_id = False
            self.prioritization_id = False
            return

        p = self.partner_id

        # ── Contact fields ──────────────────────────────────────
        self.email   = p.email   or self.email
        # self.mobile  = p.mobile  or self.mobile
        self.phone   = p.phone   or self.phone
        self.address = p.street  or self.address
        self.city    = p.city    or self.city
        if p.country_id:
            self.country_id = p.country_id
        if hasattr(p, 'nationality_id') and p.nationality_id:
            self.nationality_id = p.nationality_id

        # ── CRM & Prioritization ────────────────────────────────
        lead = self._find_crm_lead(p)
        if lead:
            self.crm_lead_id = lead.id
            prio = self._find_prioritization(lead)
            if prio:
                self.prioritization_id = prio.id
            else:
                self.prioritization_id = False
        else:
            self.crm_lead_id = False
            self.prioritization_id = False

    @api.onchange('crm_lead_id')
    def _onchange_crm_lead_id(self):
        """Allow manual lead selection to also refresh the prioritization."""
        if self.crm_lead_id:
            prio = self._find_prioritization(self.crm_lead_id)
            self.prioritization_id = prio.id if prio else False
        else:
            self.prioritization_id = False

    # ─────────────────────────────────────────────
    # Identification
    # ─────────────────────────────────────────────
    id_type = fields.Selection([
        ('national_id', 'National ID'),
        ('passport', 'Passport'),
        ('residence_permit', 'Residence Permit'),
        ('driving_license', 'Driving License'),
    ], string='ID Type', required=True)
    id_number = fields.Char(string='ID Number', required=True, tracking=True)
    id_expiry_date = fields.Date(string='ID Expiry Date')
    id_issue_place = fields.Char(string='ID Issue Place')
    tax_id = fields.Char(string='Tax ID / TIN')

    # ─────────────────────────────────────────────
    # Financial Information
    # ─────────────────────────────────────────────
    employment_status = fields.Selection([
        ('employed', 'Employed'),
        ('self_employed', 'Self Employed'),
        ('business_owner', 'Business Owner'),
        ('retired', 'Retired'),
        ('unemployed', 'Unemployed'),
    ], string='Employment Status', required=True)
    employer_name = fields.Char(string='Employer / Business Name')
    job_title = fields.Char(string='Job Title')
    years_employed = fields.Integer(string='Years with Current Employer')

    monthly_income = fields.Monetary(string='Monthly Income', currency_field='currency_id',
                                     required=True, tracking=True)
    other_income = fields.Monetary(string='Other Monthly Income', currency_field='currency_id')
    total_monthly_income = fields.Monetary(string='Total Monthly Income',
                                           compute='_compute_total_income',
                                           currency_field='currency_id', store=True)
    monthly_obligations = fields.Monetary(string='Monthly Financial Obligations',
                                          currency_field='currency_id')
    currency_id = fields.Many2one('res.currency', string='Currency',
                                  default=lambda self: self.env.company.currency_id)
    debt_burden_ratio = fields.Float(string='Debt Burden Ratio (%)',
                                     compute='_compute_dbr', store=True)

    # Credit
    credit_score = fields.Integer(string='Credit Score')
    credit_rating = fields.Selection([
        ('excellent', 'Excellent (750+)'),
        ('good', 'Good (700-749)'),
        ('fair', 'Fair (650-699)'),
        ('poor', 'Poor (600-649)'),
        ('very_poor', 'Very Poor (<600)'),
    ], string='Credit Rating')
    has_existing_loans = fields.Boolean(string='Has Existing Loans')
    existing_loans_detail = fields.Text(string='Existing Loans Detail')

    # ─────────────────────────────────────────────
    # Property & Financing
    # ─────────────────────────────────────────────
    property_id = fields.Many2one(
        'property.details',
        string='Selected Property',
        required=True,
        tracking=True,
        domain="[('stage', 'in', ['available', 'reserved', 'booked'])]",
    )
    # Mirror fields auto-filled from property.details on selection
    property_price = fields.Monetary(
        string='Property Price',
        currency_field='currency_id',
        related='property_id.price',
        store=True,
    )
    property_code = fields.Char(
        string='Property Code',
        related='property_id.property_seq',
        store=True,
        readonly=True,
    )
    property_type_mirror = fields.Selection(
    related="property_id.type",
    string="Property Type",
    store=True,
    readonly=True,
    )
    property_city = fields.Char(
        related='property_id.city',
        string='Property City',
        store=True,
        readonly=True,
    )
    property_total_area = fields.Float(
        related='property_id.total_area',
        string='Total Area',
        store=True,
        readonly=True,
    )
    property_project = fields.Many2one(
        'property.project',
        related='property_id.property_project_id',
        string='Project',
        store=True,
        readonly=True,
    )
    property_subproject = fields.Many2one(
        'property.sub.project',
        related='property_id.subproject_id',
        string='Sub Project',
        store=True,
        readonly=True,
    )
    property_landlord = fields.Many2one(
        'res.partner',
        related='property_id.landlord_id',
        string='Landlord',
        store=True,
        readonly=True,
    )
    property_bed = fields.Integer(
        related='property_id.bed',
        string='Rooms',
        store=True,
        readonly=True,
    )
    property_bathroom = fields.Integer(
        related='property_id.bathroom',
        string='Bathrooms',
        store=True,
        readonly=True,
    )
    property_floor = fields.Integer(
        related='property_id.floor',
        string='Floor',
        store=True,
        readonly=True,
    )
    property_parking = fields.Integer(
        related='property_id.parking',
        string='Parking',
        store=True,
        readonly=True,
    )

    financing_type = fields.Selection([
        ('murabaha', 'Murabaha (Islamic)'),
        ('ijara', 'Ijara (Islamic Lease)'),
        ('diminishing_musharaka', 'Diminishing Musharaka'),
        ('conventional', 'Conventional Mortgage'),
        ('cash', 'Cash Purchase'),
    ], string='Preferred Financing Type', required=True, tracking=True)
    is_cash_purchase = fields.Boolean(
        string='Cash Purchase',
        compute='_compute_is_cash',
        store=True,
        help='True when financing_type is Cash Purchase — hides bank financing fields.',
    )
    financing_amount = fields.Monetary(string='Financing Amount Required',
                                       currency_field='currency_id', tracking=True)
    down_payment = fields.Monetary(string='Down Payment / Total Cash Amount',
                                   currency_field='currency_id')
    down_payment_pct = fields.Float(string='Down Payment (%)',
                                    compute='_compute_down_payment_pct', store=True)
    tenure_months = fields.Integer(string='Requested Tenure (months)', default=240)
    expected_monthly_payment = fields.Monetary(string='Expected Monthly Payment',
                                               currency_field='currency_id')

    # Sharia Compliance
    is_sharia_compliant_request = fields.Boolean(string='Sharia Compliant Request',
                                                 default=True, tracking=True)
    sharia_compliance_note = fields.Text(string='Sharia Compliance Notes')
    sharia_review_date = fields.Date(string='Sharia Review Date')
    sharia_reviewer_id = fields.Many2one('res.users', string='Sharia Reviewer')

    # ─────────────────────────────────────────────
    # Bank Review
    # ─────────────────────────────────────────────
    submission_date = fields.Datetime(string='Submission Date', readonly=True)
    review_start_date = fields.Datetime(string='Review Start Date', readonly=True)
    decision_date = fields.Datetime(string='Decision Date', readonly=True)
    approved_amount = fields.Monetary(string='Approved Amount', currency_field='currency_id',
                                      tracking=True)
    approved_tenure = fields.Integer(string='Approved Tenure (months)')
    approved_rate = fields.Float(string='Approved Rate (%)')
    rejection_reason = fields.Text(string='Rejection Reason', tracking=True)
    bank_notes = fields.Text(string='Bank Officer Notes')
    conditions = fields.Text(string='Approval Conditions')

    # ─────────────────────────────────────────────
    # Related Records
    # ─────────────────────────────────────────────
    financing_request_ids = fields.One2many('bre.financing.request', 'application_id',
                                            string='Financing Requests')
    financing_request_count = fields.Integer(compute='_compute_financing_count')
    document_ids = fields.One2many('bre.document.attachment', 'application_id',
                                   string='Documents')
    document_count = fields.Integer(compute='_compute_document_count')
    required_documents = fields.Many2many('bre.document.type', string='Required Documents')

    # Dates
    application_date = fields.Date(string='Application Date', default=fields.Date.today)
    expected_completion_date = fields.Date(string='Expected Completion Date')

    # ─────────────────────────────────────────────
    # Computed / UI
    # ─────────────────────────────────────────────
    progress = fields.Integer(string='Progress', compute='_compute_progress')
    color = fields.Integer(string='Color Index', compute='_compute_color')

    # ─────────────────────────────────────────────
    # Property Classification (from property.details)
    # ─────────────────────────────────────────────
    property_zone = fields.Many2one(
        'property.zone',
        related='property_id.zone',
        string='Zone',
        store=True, readonly=True,
    )
    property_lot = fields.Many2one(
        'property.lot',
        related='property_id.lot',
        string='Lot',
        store=True, readonly=True,
    )
    property_block = fields.Many2one(
        'property.block',
        related='property_id.block',
        string='Block',
        store=True, readonly=True,
    )
    property_tf_no = fields.Char(
        related='property_id.tf_no',
        string='TF N#',
        store=True, readonly=True,
    )
    property_sequence_no = fields.Char(
        related='property_id.property_sequence_no',
        string='Property ID',
        store=True, readonly=True,
    )
    property_is_apartment = fields.Boolean(
        related='property_id.property_subtype_id.is_apartment',
        string='Is Apartment',
        store=True, readonly=True,
    )

    # ─────────────────────────────────────────────
    # ORM Overrides
    # ─────────────────────────────────────────────
    # ─────────────────────────────────────────────
    # Default / ORM
    # ─────────────────────────────────────────────
    def _default_stage(self):
        return self.env['bre.application.stage'].search([], order='sequence asc', limit=1)

    @api.model
    def _read_group_stage_ids(self, stages, domain):
        return self.env['bre.application.stage'].search([], order='sequence asc')

    def write(self, vals):
        # Block moving cash purchase applications to bank stages
        if 'stage_id' in vals and vals['stage_id']                 and not self.env.context.get('skip_cash_stage_check'):
            new_stage = self.env['bre.application.stage'].browse(vals['stage_id'])
            if new_stage.stage_type == 'bank' or new_stage.name == 'Submitted to Bank':
                for rec in self:
                    if rec.is_cash_purchase:
                        raise UserError(_(
                            'This application financing type is a Cash Purchase.'
                        ))
        res = super().write(vals)
        if 'stage_id' in vals:
            for rec in self:
                if rec.stage_id and rec.stage_id.is_confirmed and rec.property_id:
                    if rec.property_id.stage not in ('booked',):
                        rec.property_id.sudo().write({'stage': 'booked'})
                        rec.message_post(
                            body=_('Property <b>%s</b> automatically set to <b>Booked</b> '
                                   'upon reaching the Confirmed stage.') % rec.property_id.name,
                            subtype_xmlid='mail.mt_note',
                        )
        return res

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('bre.customer.application') or 'New'
        return super().create(vals_list)

    # ─────────────────────────────────────────────
    # Compute Methods
    # ─────────────────────────────────────────────
    @api.depends('date_of_birth')
    def _compute_age(self):
        today = date.today()
        for rec in self:
            if rec.date_of_birth:
                rec.age = today.year - rec.date_of_birth.year - (
                    (today.month, today.day) < (rec.date_of_birth.month, rec.date_of_birth.day)
                )
            else:
                rec.age = 0

    @api.depends('monthly_income', 'other_income')
    def _compute_total_income(self):
        for rec in self:
            rec.total_monthly_income = rec.monthly_income + rec.other_income

    @api.depends('monthly_obligations', 'total_monthly_income')
    def _compute_dbr(self):
        for rec in self:
            if rec.total_monthly_income:
                rec.debt_burden_ratio = (rec.monthly_obligations / rec.total_monthly_income) * 100
            else:
                rec.debt_burden_ratio = 0.0

    @api.depends('financing_type')
    def _compute_is_cash(self):
        for rec in self:
            rec.is_cash_purchase = rec.financing_type == 'cash'

    @api.onchange('stage_id')
    def _onchange_stage_id_block_bank(self):
        """Warn and reset if cash purchase tries to move to a bank stage."""
        if not self.is_cash_purchase:
            return
        if not self.stage_id:
            return
        bank_stage_names = ['Submitted to Bank', 'Bank Review', 'Sharia Review']
        if self.stage_id.stage_type == 'bank' or self.stage_id.name in bank_stage_names:
            # Reset to previous allowed stage
            allowed = self.env['bre.application.stage'].search(
                [('stage_type', 'not in', ['bank']),
                 ('name', 'not in', ['Submitted to Bank'])],
                order='sequence asc', limit=1
            )
            self.stage_id = self._origin.stage_id or allowed
            return {
                'warning': {
                    'title': 'Not Allowed for Cash Purchase',
                    'message': 'This application financing type is a Cash Purchase.',
                }
            }



    @api.depends('down_payment', 'property_price')
    def _compute_down_payment_pct(self):
        for rec in self:
            if rec.property_price:
                rec.down_payment_pct = (rec.down_payment / rec.property_price) * 100
            else:
                rec.down_payment_pct = 0.0

    @api.depends('financing_request_ids')
    def _compute_financing_count(self):
        for rec in self:
            rec.financing_request_count = len(rec.financing_request_ids)

    @api.depends('document_ids')
    def _compute_document_count(self):
        for rec in self:
            rec.document_count = len(rec.document_ids)

    @api.depends('stage_id')
    def _compute_progress(self):
        stages = self.env['bre.application.stage'].search([], order='sequence asc')
        stage_list = stages.ids
        for rec in self:
            if rec.stage_id and stage_list:
                idx = stage_list.index(rec.stage_id.id) + 1 if rec.stage_id.id in stage_list else 1
                rec.progress = int((idx / len(stage_list)) * 100)
            else:
                rec.progress = 0

    @api.depends('bank_status')
    def _compute_color(self):
        color_map = {
            'not_submitted': 0,
            'pending': 3,
            'under_review': 4,
            'approved': 10,
            'rejected': 1,
            'on_hold': 2,
        }
        for rec in self:
            rec.color = color_map.get(rec.bank_status, 0)

    # ─────────────────────────────────────────────
    # Constraints
    # ─────────────────────────────────────────────
    @api.constrains('financing_amount', 'property_price')
    def _check_financing_amount(self):
        for rec in self:
            # Cash purchases do not have a financing amount — skip this check
            if rec.is_cash_purchase:
                continue
            if rec.financing_amount and rec.financing_amount > rec.property_price:
                raise ValidationError(
                    _('Financing amount cannot exceed the property price.')
                )

    @api.constrains('date_of_birth')
    def _check_age(self):
        for rec in self:
            if rec.date_of_birth and rec.age < 18:
                raise ValidationError(_('Customer must be at least 18 years old.'))

    # ─────────────────────────────────────────────
    # Workflow Actions
    # ─────────────────────────────────────────────
    def action_submit_to_bank(self):
        self.ensure_one()
        if self.is_cash_purchase:
            raise UserError(_(
                'This is a Cash Purchase application — bank financing submission is not applicable.'
            ))
        self.write({
            'bank_status': 'pending',
            'submission_date': fields.Datetime.now(),
        })
        # Create financing request automatically
        self.env['bre.financing.request'].create({
            'application_id': self.id,
            'agent_id': self.agent_id.id,
            'bank_officer_id': self.bank_officer_id.id,
            'financing_type': self.financing_type,
            'requested_amount': self.financing_amount,
            'requested_tenure': self.tenure_months,
            'status': 'submitted',
        })
        self.message_post(body=_('Application submitted to bank for review.'),
                          subtype_xmlid='mail.mt_note')
        # Notify bank officer if assigned
        if self.bank_officer_id:
            self.activity_schedule(
                'mail.mail_activity_data_todo',
                user_id=self.bank_officer_id.id,
                summary=_('New financing application to review'),
                note=_('Please review application %s') % self.name,
            )

    def action_start_review(self):
        self.ensure_one()
        self.write({
            'bank_status': 'under_review',
            'review_start_date': fields.Datetime.now(),
            'bank_officer_id': self.env.user.id,
        })
        self.message_post(body=_('Application is now under review by %s.') % self.env.user.name,
                          subtype_xmlid='mail.mt_note')

    def action_approve(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Approve Application'),
            'res_model': 'bre.approval.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_application_id': self.id},
        }

    def action_reject(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Reject Application'),
            'res_model': 'bre.rejection.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_application_id': self.id},
        }

    def action_put_on_hold(self):
        self.write({'bank_status': 'on_hold'})
        self.message_post(body=_('Application placed on hold.'), subtype_xmlid='mail.mt_note')

    def action_resubmit(self):
        self.write({'bank_status': 'pending', 'submission_date': fields.Datetime.now()})
        self.message_post(body=_('Application resubmitted for review.'), subtype_xmlid='mail.mt_note')

    def action_view_documents(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Documents',
            'res_model': 'bre.document.attachment',
            'view_mode': 'list,form',
            'domain': [('application_id', '=', self.id)],
            'context': {'default_application_id': self.id},
        }

    def action_view_financing_requests(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Financing Requests',
            'res_model': 'bre.financing.request',
            'view_mode': 'list,form',
            'domain': [('application_id', '=', self.id)],
            'context': {'default_application_id': self.id},
        }

    def action_print_report(self):
        return self.env.ref('bank_realestate_collab.action_report_application').report_action(self)

    def name_get(self):
        result = []
        for rec in self:
            label = rec.partner_id.name if rec.partner_id else rec.customer_name or '?'
            result.append((rec.id, f"[{rec.name}] {label}"))
        return result


class ApplicationStage(models.Model):
    _name = 'bre.application.stage'
    _description = 'Application Stage'
    _order = 'sequence asc'

    name = fields.Char(string='Stage Name', required=True, translate=True)
    sequence = fields.Integer(string='Sequence', default=10)
    fold = fields.Boolean(string='Folded in Kanban')
    is_final = fields.Boolean(string='Final Stage')
    is_confirmed = fields.Boolean(
        string='Confirmed Stage',
        default=False,
        help='When an application moves into this stage, '
             'the linked property is automatically set to Booked.',
    )
    description = fields.Text(string='Description')
    color = fields.Integer(string='Color')
    stage_type = fields.Selection([
        ('agent', 'Real Estate Stage'),
        ('bank', 'Bank Stage'),
        ('shared', 'Shared'),
    ], string='Stage Type', default='shared')
