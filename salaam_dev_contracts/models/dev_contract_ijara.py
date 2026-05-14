# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError


class DevContractIjara(models.Model):
    _name = 'dev.contract.ijara'
    _description = 'Ijara Lease Contract'
    _inherit = ['dev.contract.base']

    milestone_ids = fields.One2many(
        'dev.contract.milestone', 'contract_id',
        string='Milestones',
        context={'default_res_model': 'dev.contract.ijara'},
    )

    contract_type = fields.Selection(default='ijara')
    sharia_required = fields.Boolean(default=True, readonly=True)

    # ── PARTIES ──────────────────────────────────────────────────────────────
    lessee_id = fields.Many2one(
        'res.partner', string='Lessee (Tenant)', required=True, tracking=True,
    )
    lessor_id = fields.Many2one(
        'res.partner', string='Lessor',
        default=lambda self: self.env.company.partner_id,
        required=True,
    )

    # ── IJARA TYPE ────────────────────────────────────────────────────────────
    ijara_type = fields.Selection(
        selection=[
            ('operating', 'Operating Lease (Ijara)'),
            ('muntahia', 'Lease to Own (Ijara Muntahia Bittamleek)'),
        ],
        string='Ijara Type', required=True, default='operating', tracking=True,
    )

    # ── FINANCIAL TERMS ───────────────────────────────────────────────────────
    monthly_rental = fields.Monetary(
        string='Monthly Rental', currency_field='currency_id', required=True,
    )
    annual_rental = fields.Monetary(
        string='Annual Rental Value', compute='_compute_annual_rental',
        currency_field='currency_id', store=True,
    )
    rental_escalation_rate = fields.Float(
        string='Annual Escalation Rate (%)', digits=(5, 2),
        help='Annual rental increase percentage agreed at contract signing',
    )
    rental_escalation_basis = fields.Selection(
        selection=[
            ('fixed_rate', 'Fixed Rate'),
            ('cpi_linked', 'CPI Linked'),
            ('mutual_agreement', 'By Mutual Agreement'),
        ],
        string='Escalation Basis', default='fixed_rate',
    )
    security_deposit = fields.Monetary(
        string='Security Deposit', currency_field='currency_id',
    )

    # ── OBLIGATIONS ───────────────────────────────────────────────────────────
    maintenance_obligation = fields.Selection(
        selection=[
            ('bank', 'Bank (Lessor)'),
            ('lessee', 'Lessee'),
            ('shared', 'Shared'),
        ],
        string='Maintenance Obligation', required=True, default='bank',
    )
    subletting_permitted = fields.Boolean(
        string='Subletting Permitted', default=False,
    )

    # ── PURCHASE OPTION (Muntahia Bittamleek only) ────────────────────────────
    purchase_option_price = fields.Monetary(
        string='Purchase Option Price', currency_field='currency_id',
    )
    purchase_option_date = fields.Date(
        string='Earliest Purchase Option Date',
    )
    purchase_option_exercised = fields.Boolean(
        string='Purchase Option Exercised', default=False, readonly=True,
    )

    # ── LINKED RENT CONTRACT ──────────────────────────────────────────────────
    linked_rent_contract_id = fields.Many2one(
        'tenancy.details', string='Linked Rental Contract',
        help='Linked record in rental_management when auto-created on signing',
        ondelete='set null',
    )

    # ── SHARIA ────────────────────────────────────────────────────────────────
    aaoifi_standard_ref = fields.Char(
        string='AAOIFI Standard Reference',
        default='AAOIFI FAS 8 — Ijarah and Ijarah Muntahia Bittamleek',
    )

    # ── COMPUTED ──────────────────────────────────────────────────────────────
    @api.depends('monthly_rental')
    def _compute_annual_rental(self):
        for rec in self:
            rec.annual_rental = (rec.monthly_rental or 0) * 12

    def _get_sequence_code(self):
        return 'dev.contract.ijara'

    def action_sign(self):
        super().action_sign()
        # Optionally auto-create a rent.contract in rental_management
        config = self.env['ir.config_parameter'].sudo()
        if config.get_param('salaam_dev_contracts.ijara_auto_create_rent', False):
            self._create_linked_rent_contract()

    def _create_linked_rent_contract(self):
        """Create a corresponding rental_management rent.contract on signing."""
        self.ensure_one()
        if self.linked_rent_contract_id:
            return
        if 'tenancy.details' not in self.env:
            return
        rent = self.env['tenancy.details'].create({
            'partner_id': self.lessee_id.id,
            'property_id': self.property_id.id if self.property_id else False,
            'date_start': self.date_start,
            'date_end': self.date_end,
            'rent': self.monthly_rental,
        })
        self.linked_rent_contract_id = rent

    def action_exercise_purchase_option(self):
        self.ensure_one()
        if self.ijara_type != 'muntahia':
            raise UserError(_('Purchase option is only available for Ijara Muntahia Bittamleek contracts.'))
        if self.state != 'active':
            raise UserError(_('Contract must be Active to exercise the purchase option.'))
        self.purchase_option_exercised = True
        self.message_post(
            body=_('Purchase option exercised by %s on %s.') % (
                self.env.user.name, fields.Date.today()
            )
        )

    @api.onchange('ijara_type')
    def _onchange_ijara_type(self):
        if self.ijara_type == 'operating':
            self.purchase_option_price = 0
            self.purchase_option_date = False

    def _check_required_fields(self):
        for rec in self:
            if not rec.lessee_id:
                raise ValidationError(_('Lessee is required before submitting an Ijara contract.'))
