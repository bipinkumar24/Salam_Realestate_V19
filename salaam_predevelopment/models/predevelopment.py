# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError
from datetime import date


class SalaamPredevelopment(models.Model):
    """
    Pre-Development Pipeline Application.

    Tracks a real estate development from initial idea through to
    design completion and handover to the construction/sales teams.

    Stage flow:
      market_research → land → feasibility → concept → unit_mix → design → approved

    Links to downstream modules at each stage:
      land          → salaam.project (creates or links the master project)
      unit_mix      → property.details (auto-creates unit records)
      design        → salaam.tender (triggers design/construction tender)
      approved      → project.project (opens construction)
    """
    _name = 'salaam.predevelopment'
    _description = 'Pre-Development Application'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'name desc'

    # ── IDENTITY ──────────────────────────────────────────────────────────────
    name = fields.Char(
        string='Application Reference',
        readonly=True, copy=False, default='New',
    )
    title = fields.Char(
        string='Development Title', required=True,
        tracking=True,
    )
    stage = fields.Selection([
        ('market_research', 'Market Research'),
        ('land',            'Land Acquisition'),
        ('feasibility',     'Feasibility Study'),
        ('concept',         'Concept Design'),
        ('unit_mix',        'Unit Mix'),
        ('design',          'Design'),
        ('approved',        'Approved — Handed Over'),
        ('cancelled',       'Cancelled'),
    ], string='Stage', default='market_research',
       tracking=True, required=True)

    # ── PROJECT LINK ──────────────────────────────────────────────────────────
    project_id = fields.Many2one(
        'salaam.project',
        string='Development / Project',
        tracking=True,
        help='Links to the master development project once land is confirmed',
    )
    sub_project_id = fields.Many2one(
        'salaam.sub.project',
        string='Sub Project / Phase',
        domain="[('project_id', '=', project_id)]",
    )

    # ── LOCATION ─────────────────────────────────────────────────────────────
    location = fields.Char(string='Location / Address')
    city = fields.Char(string='City')
    country_id = fields.Many2one('res.country', string='Country',
                                 default=lambda self: self.env.ref('base.dj', raise_if_not_found=False))
    land_area = fields.Float(string='Land Area (m²)')
    gfa = fields.Float(string='GFA (m²)', help='Gross Floor Area')
    plot_ratio = fields.Float(string='Plot Ratio / FAR')

    # ── TEAM ─────────────────────────────────────────────────────────────────
    developer_id = fields.Many2one('res.partner', string='Developer / Owner')
    project_manager_id = fields.Many2one('res.users', string='Project Manager',
                                          default=lambda self: self.env.user)
    architect_id = fields.Many2one('res.partner', string='Architect / Lead Designer')

    # ── TIMELINE ─────────────────────────────────────────────────────────────
    start_date = fields.Date(string='Start Date', default=fields.Date.today)
    target_launch_date = fields.Date(string='Target Sales Launch Date')
    target_completion_date = fields.Date(string='Target Completion Date')

    # ── FINANCIALS ───────────────────────────────────────────────────────────
    currency_id = fields.Many2one(
        'res.currency', default=lambda self: self.env.company.currency_id,
    )
    land_cost = fields.Monetary(string='Land Cost', currency_field='currency_id')
    estimated_build_cost = fields.Monetary(string='Estimated Build Cost',
                                            currency_field='currency_id')
    estimated_gdc = fields.Monetary(string='Estimated GDC (Total)',
                                     currency_field='currency_id',
                                     compute='_compute_financials', store=True)
    estimated_gdv = fields.Monetary(string='Estimated GDV',
                                     currency_field='currency_id')
    estimated_margin = fields.Float(string='Development Margin (%)',
                                     compute='_compute_financials', store=True)
    viability_status = fields.Selection([
        ('not_assessed', 'Not Assessed'),
        ('viable',       'Viable'),
        ('marginal',     'Marginal — Review Required'),
        ('not_viable',   'Not Viable'),
    ], string='Viability', default='not_assessed')

    @api.depends('land_cost', 'estimated_build_cost', 'estimated_gdv')
    def _compute_financials(self):
        for rec in self:
            gdc = (rec.land_cost or 0) + (rec.estimated_build_cost or 0)
            rec.estimated_gdc = gdc
            if rec.estimated_gdv:
                rec.estimated_margin = ((rec.estimated_gdv - gdc) / rec.estimated_gdv) * 100
            else:
                rec.estimated_margin = 0.0

    # ── UNIT MIX ─────────────────────────────────────────────────────────────
    unit_mix_ids = fields.One2many(
        'salaam.predevelopment.unit.mix', 'predevelopment_id',
        string='Unit Mix',
    )
    total_units = fields.Integer(
        string='Total Units', compute='_compute_unit_totals', store=True,
    )
    total_sellable_area = fields.Float(
        string='Total Sellable Area (m²)', compute='_compute_unit_totals', store=True,
    )

    @api.depends('unit_mix_ids.quantity', 'unit_mix_ids.unit_area')
    def _compute_unit_totals(self):
        for rec in self:
            rec.total_units = sum(l.quantity for l in rec.unit_mix_ids)
            rec.total_sellable_area = sum(
                l.quantity * l.unit_area for l in rec.unit_mix_ids
            )

    # ── DOWNSTREAM LINKS ─────────────────────────────────────────────────────
    tender_ids = fields.One2many(
        'salaam.tender', 'predevelopment_id',
        string='Design / Construction Tenders',
    )
    tender_count = fields.Integer(compute='_compute_tender_count')
    construction_project_id = fields.Many2one(
        'project.project',
        string='Construction Project',
        readonly=True,
        help='Auto-linked or created when development is approved',
    )
    units_created = fields.Boolean(
        string='Property Units Created', default=False, readonly=True,
    )
    property_ids = fields.One2many(
        'property.details', 'predevelopment_id',
        string='Property Units',
    )
    property_count = fields.Integer(compute='_compute_property_count')

    def _compute_tender_count(self):
        for rec in self:
            rec.tender_count = len(rec.tender_ids)

    def _compute_property_count(self):
        for rec in self:
            rec.property_count = len(rec.property_ids)

    # ── STAGE NOTES ──────────────────────────────────────────────────────────
    market_research_notes = fields.Text(string='Market Research Summary')
    land_notes = fields.Text(string='Land Acquisition Notes')
    feasibility_notes = fields.Text(string='Feasibility Study Summary')
    concept_notes = fields.Text(string='Concept Design Notes')
    design_notes = fields.Text(string='Design Notes')
    internal_notes = fields.Text(string='Internal Notes')

    # ── DOCUMENTS / ATTACHMENTS COUNT ────────────────────────────────────────
    attachment_count = fields.Integer(compute='_compute_attachment_count')

    def _compute_attachment_count(self):
        for rec in self:
            rec.attachment_count = self.env['ir.attachment'].search_count([
                ('res_model', '=', self._name),
                ('res_id', '=', rec.id),
            ])

    # ── SEQUENCE ─────────────────────────────────────────────────────────────
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'salaam.predevelopment'
                ) or _('New')
        return super().create(vals_list)

    # ── STAGE TRANSITIONS ────────────────────────────────────────────────────
    def _check_stage_requirements(self, target_stage):
        self.ensure_one()
        errors = []
        if target_stage == 'land':
            if not self.location:
                errors.append(_('Location must be set before moving to Land Acquisition.'))
        if target_stage == 'feasibility':
            if not self.land_area:
                errors.append(_('Land Area must be set before Feasibility Study.'))
            if not self.developer_id:
                errors.append(_('Developer / Owner must be set.'))
        if target_stage == 'concept':
            if self.viability_status == 'not_viable':
                errors.append(_('Project is marked Not Viable — cannot proceed to Concept.'))
            if self.viability_status == 'not_assessed':
                errors.append(_('Viability must be assessed before moving to Concept Design.'))
        if target_stage == 'unit_mix':
            if not self.project_id:
                errors.append(_('A Development / Project must be linked before Unit Mix.'))
            if not self.architect_id:
                errors.append(_('An Architect / Lead Designer must be assigned.'))
        if target_stage == 'design':
            if not self.unit_mix_ids:
                errors.append(_('Unit Mix must be defined before moving to Design stage.'))
        if target_stage == 'approved':
            if not self.units_created:
                errors.append(_('Property units must be created from the Unit Mix before approval.'))
        if errors:
            raise UserError('\n'.join(errors))

    def action_next_stage(self):
        """Advance to the next stage with validation."""
        stage_order = [
            'market_research', 'land', 'feasibility',
            'concept', 'unit_mix', 'design', 'approved',
        ]
        for rec in self:
            if rec.stage == 'approved':
                raise UserError(_('This development is already approved.'))
            if rec.stage == 'cancelled':
                raise UserError(_('Cannot advance a cancelled development.'))
            idx = stage_order.index(rec.stage)
            next_stage = stage_order[idx + 1]
            rec._check_stage_requirements(next_stage)
            rec.stage = next_stage
            rec.message_post(body=_('Stage advanced to: <b>%s</b>') % dict(
                rec._fields['stage'].selection)[next_stage])

    def action_cancel(self):
        for rec in self:
            if rec.stage == 'approved':
                raise UserError(_('Cannot cancel an approved development.'))
            rec.stage = 'cancelled'

    def action_reset_draft(self):
        for rec in self:
            rec.stage = 'market_research'

    # ── CREATE UNITS FROM UNIT MIX ────────────────────────────────────────────
    def action_create_units(self):
        """
        Create property.details records from the unit mix lines.
        Each unit mix line generates N units with sequential unit numbers.
        Links back to this predevelopment, project, and sub-project.
        """
        self.ensure_one()
        if self.units_created:
            raise UserError(_('Units have already been created for this development.'))
        if not self.unit_mix_ids:
            raise UserError(_('Define the Unit Mix before creating units.'))
        if self.stage not in ('unit_mix', 'design', 'approved'):
            raise UserError(_('Move to Unit Mix stage before creating units.'))
        if not self.project_id:
            raise UserError(_('Link a Development / Project before creating units.'))

        created = self.env['property.details']
        for line in self.unit_mix_ids:
            for i in range(1, line.quantity + 1):
                unit_name = f'{line.unit_type_code or line.unit_type}-{str(i).zfill(3)}'
                if self.sub_project_id:
                    unit_name = f'{self.sub_project_id.code or self.sub_project_id.name}-{unit_name}'
                vals = {
                    'name': unit_name,
                    'predevelopment_id': self.id,
                    'salaam_project_id': self.project_id.id,
                    'salaam_sub_project_id': self.sub_project_id.id if self.sub_project_id else False,
                    'price': line.sale_price,
                }
                try:
                    created |= self.env['property.details'].create(vals)
                except Exception:
                    pass

        if created:
            self.units_created = True
            self.message_post(body=_(
                '%d property units created from Unit Mix.'
            ) % len(created))
        return True

    # ── CREATE DESIGN TENDER ──────────────────────────────────────────────────
    def action_create_tender(self):
        """Create a design/consultancy tender linked to this development."""
        self.ensure_one()
        if self.stage not in ('design', 'concept', 'unit_mix', 'approved'):
            raise UserError(_('Move to at least Concept stage before creating a tender.'))
        tender = self.env['salaam.tender'].create({
            'title': f'Design Consultancy — {self.title}',
            'predevelopment_id': self.id,
            'package_type': 'design',
            'tender_type': 'selective',
        })
        self.message_post(body=_('Tender <b>%s</b> created.') % tender.name)
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'salaam.tender',
            'res_id': tender.id,
            'view_mode': 'form',
        }

    # ── OPEN LINKED RECORDS ───────────────────────────────────────────────────
    def action_open_tenders(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Tenders — %s') % self.title,
            'res_model': 'salaam.tender',
            'view_mode': 'tree,form',
            'domain': [('predevelopment_id', '=', self.id)],
            'context': {'default_predevelopment_id': self.id,
                        'default_package_type': 'design'},
        }

    def action_open_units(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Units — %s') % self.title,
            'res_model': 'property.details',
            'view_mode': 'tree,form',
            'domain': [('predevelopment_id', '=', self.id)],
        }

    def action_open_attachments(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Documents — %s') % self.title,
            'res_model': 'ir.attachment',
            'view_mode': 'tree,form',
            'domain': [('res_model', '=', self._name), ('res_id', '=', self.id)],
        }
