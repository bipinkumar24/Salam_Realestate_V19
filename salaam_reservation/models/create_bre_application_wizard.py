# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError
from datetime import date


class CreateBreApplicationWizard(models.TransientModel):
    """
    Wizard to collect required fields before creating a bre.customer.application.
    Pre-fills from the reservation and partner where possible.
    User reviews and completes before the application is created.
    """
    _name = 'salaam.create.bre.application.wizard'
    _description = 'Create BRE Application Wizard'

    reservation_id = fields.Many2one(
        'salaam.reservation', string='Reservation',
        required=True, readonly=True,
    )

    # ── Customer Info (pre-filled from partner) ───────────────────────────────
    partner_id = fields.Many2one('res.partner', string='Customer', readonly=True)
    customer_name = fields.Char(string='Full Name', readonly=True)

    date_of_birth = fields.Date(string='Date of Birth', required=True)
    gender = fields.Selection([
        ('male', 'Male'),
        ('female', 'Female'),
    ], string='Gender', required=True, default='male')
    nationality_id = fields.Many2one(
        'res.country', string='Nationality', required=True,
    )

    # ── Identification ────────────────────────────────────────────────────────
    id_type = fields.Selection([
        ('national_id',       'National ID'),
        ('passport',          'Passport'),
        ('residence_permit',  'Residence Permit'),
        ('driving_license',   'Driving License'),
    ], string='ID Type', required=True, default='national_id')
    id_number = fields.Char(string='ID Number', required=True)

    # ── Contact ───────────────────────────────────────────────────────────────
    email = fields.Char(string='Email', required=True)
    mobile = fields.Char(string='Mobile', required=True)

    # ── Employment & Income ───────────────────────────────────────────────────
    employment_status = fields.Selection([
        ('employed',       'Employed'),
        ('self_employed',  'Self Employed'),
        ('business_owner', 'Business Owner'),
        ('retired',        'Retired'),
        ('unemployed',     'Unemployed'),
    ], string='Employment Status', required=True, default='employed')
    employer_name = fields.Char(string='Employer / Business Name')
    monthly_income = fields.Monetary(
        string='Monthly Income', currency_field='currency_id', required=True,
    )
    currency_id = fields.Many2one(
        'res.currency',
        default=lambda self: self.env.company.currency_id,
    )

    # ── Financing ─────────────────────────────────────────────────────────────
    financing_type = fields.Selection([
        ('murabaha',             'Murabaha (Islamic)'),
        ('ijara',                'Ijara (Islamic Lease)'),
        ('diminishing_musharaka','Diminishing Musharaka'),
        ('conventional',         'Conventional Mortgage'),
        ('cash',                 'Cash Purchase'),
    ], string='Financing Type', required=True, default='murabaha')
    down_payment = fields.Monetary(
        string='Down Payment', currency_field='currency_id',
    )
    financing_amount = fields.Monetary(
        string='Financing Amount', currency_field='currency_id',
    )
    tenure_months = fields.Integer(string='Tenure (months)', default=240)

    # ── Unit info (read-only reference) ───────────────────────────────────────
    property_id = fields.Many2one('property.details', string='Unit', readonly=True)
    unit_price = fields.Monetary(string='Unit Price', currency_field='currency_id', readonly=True)

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        reservation_id = self.env.context.get('default_reservation_id')
        if not reservation_id:
            return res

        res_rec = self.env['salaam.reservation'].browse(reservation_id)
        partner = res_rec.partner_id

        res['reservation_id'] = res_rec.id
        res['partner_id'] = partner.id
        res['customer_name'] = partner.name
        res['property_id'] = res_rec.property_id.id
        res['unit_price'] = res_rec.unit_price or 0.0
        res['down_payment'] = res_rec.deposit_amount or 0.0
        res['financing_amount'] = max(
            0, (res_rec.unit_price or 0) - (res_rec.deposit_amount or 0)
        )
        res['currency_id'] = res_rec.currency_id.id

        # Pre-fill from partner
        res['email'] = partner.email or ''
        res['mobile'] = partner.phone or ''
        res['nationality_id'] = (
            getattr(partner, 'nationality_id', partner.country_id) or
            self.env.company.country_id
        ).id if (
            getattr(partner, 'nationality_id', None) or
            partner.country_id or
            self.env.company.country_id
        ) else False

        # date_of_birth from partner if available
        dob = (
            getattr(partner, 'date_of_birth', None) or
            getattr(partner, 'birthdate_date', None)
        )
        if dob:
            res['date_of_birth'] = dob

        # gender from partner if available
        gender = getattr(partner, 'gender', None)
        if gender in ('male', 'female'):
            res['gender'] = gender

        # id fields from reservation if available
        if getattr(res_rec, 'id_type', None):
            id_map = {
                'national_id':      'national_id',
                'passport':         'passport',
                'residence':        'residence_permit',
                'residence_permit': 'residence_permit',
            }
            res['id_type'] = id_map.get(res_rec.id_type, 'national_id')
        if getattr(res_rec, 'id_number', None):
            res['id_number'] = res_rec.id_number

        return res

    def action_create(self):
        """Validate inputs and create the bre.customer.application."""
        self.ensure_one()

        # Age validation
        if self.date_of_birth:
            today = date.today()
            age = (today.year - self.date_of_birth.year -
                   ((today.month, today.day) <
                    (self.date_of_birth.month, self.date_of_birth.day)))
            if age < 18:
                raise UserError(_(
                    'Customer must be at least 18 years old. '
                    'Please enter the correct date of birth.'
                ))

        if not self.email:
            raise UserError(_('Email is required.'))
        if not self.mobile:
            raise UserError(_('Mobile number is required.'))
        if not self.id_number:
            raise UserError(_('ID Number is required.'))

        res = self.reservation_id

        vals = {
            'partner_id':        self.partner_id.id,
            'agent_id':          res.agent_id.id if res.agent_id else self.env.uid,
            'date_of_birth':     self.date_of_birth,
            'gender':            self.gender,
            'nationality_id':    self.nationality_id.id,
            'id_type':           self.id_type,
            'id_number':         self.id_number,
            'email':             self.email,
            'mobile':            self.mobile,
            'employment_status': self.employment_status,
            'employer_name':     self.employer_name or '',
            'monthly_income':    self.monthly_income,
            'property_id':       self.property_id.id,
            'financing_type':    self.financing_type,
            'down_payment':      self.down_payment,
            'financing_amount':  self.financing_amount,
            'tenure_months':     self.tenure_months,
            'currency_id':       self.currency_id.id,
            'application_date':  res.reservation_date or fields.Date.today(),
        }

        # Link CRM lead if available
        if res.crm_lead_id and 'crm.lead' in self.env:
            try:
                lead = self.env['crm.lead'].browse(int(res.crm_lead_id))
                if lead.exists():
                    vals['crm_lead_id'] = lead.id
            except Exception:
                pass

        app = self.env['bre.customer.application'].create(vals)

        res.write({
            'bre_application_id': app.id,
            'state': 'new_application',
        })
        res.message_post(body=_(
            'BRE Customer Application <b>%s</b> created. '
            'Reservation moved to <b>New Application</b> stage.'
        ) % app.name)

        return {
            'type': 'ir.actions.act_window',
            'name': _('BRE Customer Application'),
            'res_model': 'bre.customer.application',
            'res_id': app.id,
            'view_mode': 'form',
            'target': 'current',
        }
