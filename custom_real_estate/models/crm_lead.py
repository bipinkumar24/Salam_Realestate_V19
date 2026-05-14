from odoo import fields, models, api, _
from odoo.exceptions import ValidationError


class Areas(models.Model):
    _name = 'area.areas'
    _description = 'interested Areas'

    name = fields.Char(string='Name')
    color = fields.Integer(string='color')

class Budget(models.Model):
    _name = 'price.prices'
    _description = 'price estimation'

    name = fields.Char(string='Name')
    color = fields.Integer(string='color')


class Rooms(models.Model):
    _name = 'room.rooms'
    _description = 'bedroom Specification'

    name = fields.Char(string='Bedroom Specification', placeholder='Example: 3 Bedrooms with 2 bathrooms')
            
class Typeappartment(models.Model):
    _name = 'appart.type'
    _description = 'Appartment Type'

    name = fields.Char(string='Name')

class PropertyVendorLead(models.Model):
    _inherit = 'property.vendor'

    lead_id = fields.Many2one('crm.lead', string='Lead / Opportunity')


class LeadBooking(models.Model):
    _inherit = 'crm.lead'

    valid_until = fields.Date(string='Handover Date')
    address = fields.Char(string='Address')
    home_address = fields.Char(string='Home Address')
    areas_id = fields.Many2many('area.areas', string='Location of Interest')
    bedroom = fields.Many2one('room.rooms', string='Bedrooms', )
    prices = fields.Many2one('price.prices', string='Budget')
    garden = fields.Selection([('True', 'Yes'), ('False', 'No')], default='False', string='Requires Garden?')
    parking = fields.Selection([('True', 'Yes'), ('False', 'No')], default='False', string='Requires Parking?')
    fmode = fields.Selection(
        [('cash', 'Cash'), ('bank', 'Bank')], default='cash',
        string='Finance Mode')
    appartment_type = fields.Selection(
        [('villa', 'Villa'), ('villanoex', 'villa without extension'),
         ('villanex', 'villa with extension'), ('rawhouse', 'Raw house'),
         ('duplex', 'Duplex'),
         ('appartment', 'Appartment')],
        string='Appartment type')
        
    type_appartment = fields.Many2many('appart.type', string='Appartment Type')

        
    deposit_capabilty = fields.Selection(
        [('0%', '0%'), ('10%', '10%'), ('15%', '15%'), ('20%', '20%'), ('25%', '25%'), ('30%', '30%'), ('40%', '40%'),
         ('50%+', '50%+')], default='0%',
        string='Deposit Capability')
    source = fields.Selection(
        [('socialmedia', 'Social Media'), ('tv', 'TV'), ('radio', 'Radio'), ('walkin', 'Walk-in')],
        default='socialmedia',
        string='Source')
    description = fields.Text(string='Additional Information')
    sale_contract_ids = fields.One2many('property.vendor', 'lead_id', string='Sale Contracts')
    sale_contract_count = fields.Integer(compute='_compute_sale_contract_count', string='Sale Contracts')
    sale_property_count = fields.Integer(compute='_compute_sale_contract_count', string='Properties')
    booking_prioritization_ids = fields.One2many('unit.prioritization', 'opportunity_id', string='Orders')
    is_last = fields.Boolean(string='Last Stage', compute='_compute_is_last')
    stage_id = fields.Many2one('crm.stage')
    booking_priority_count = fields.Integer(string="Job Order", compute='_compute_booking_priority_count')
    is_prioritization = fields.Boolean('Is Prioritization', compute='_compute_is_booking_priority', store=True)
    is_prioritization_number = fields.Boolean('Is Prioritization', compute='_compute_is_booking_priority', store=True)
    is_file_number = fields.Boolean('Is File Number', compute='_compute_is_file_number', store=True)

    def _compute_sale_contract_count(self):
        for rec in self:
            rec.sale_contract_count = len(rec.sale_contract_ids)
            rec.sale_property_count = len(rec.sale_contract_ids.mapped('property_id'))

    def action_view_sale_contracts(self):
        self.ensure_one()
        contracts = self.sale_contract_ids
        action = {
            'name': _('Sale Contracts'),
            'type': 'ir.actions.act_window',
            'res_model': 'property.vendor',
            'view_mode': 'list,form',
            'domain': [('lead_id', '=', self.id)],
            'context': {'default_lead_id': self.id},
        }
        if len(contracts) == 1:
            action['view_mode'] = 'form'
            action['res_id'] = contracts.id
        return action

    def action_view_lead_property(self):
        self.ensure_one()
        property_ids = self.sale_contract_ids.mapped('property_id').ids
        action = {
            'name': _('Properties'),
            'type': 'ir.actions.act_window',
            'res_model': 'property.details',
            'view_mode': 'list,form',
            'domain': [('id', 'in', property_ids)],
        }
        if len(property_ids) == 1:
            action['view_mode'] = 'form'
            action['res_id'] = property_ids[0]
        return action

    def _compute_booking_priority_count(self):
        for line in self:
            line.booking_priority_count = len(line.booking_prioritization_ids.ids)

    @api.depends('booking_prioritization_ids.next_approval_id', 'booking_prioritization_ids.prioritization_number', 'booking_prioritization_ids')
    def _compute_is_booking_priority(self):
        for line in self:
            line.is_prioritization = True if len(line.booking_prioritization_ids.ids) != 0 else False
            line.is_prioritization_number = True if any(a.prioritization_number for a in line.booking_prioritization_ids) else False


    @api.depends('booking_prioritization_ids.file_number', 'booking_prioritization_ids.file_number', 'booking_prioritization_ids')
    def _compute_is_file_number(self):
        for line in self:
            line.is_file_number = True if any(a.file_number for a in line.booking_prioritization_ids) else False


    def unlink(self):
        user = self.env.user
        if user.has_group('custom_real_estate.cant_delete_lead'):
            raise ValidationError("You do not have the permission to delete leads.")
        return super(LeadBooking, self).unlink()

    def action_booking_new(self):
        return {
            'name': _('Booking Type'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'booking.lead',
            'target': 'new',
        }

    def action_create_booking(self):
        return {
            'name': _('Create Booking'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'crm.booking.wizard',
            'target': 'new',
        }

    def action_prioritization_booking(self):
        sata_ids = self.booking_prioritization_ids
        return {
            'name': _('Prioritization'),
            'view_mode': 'list,form',
            'res_model': 'unit.prioritization',
            'view_id': False,
            'type': 'ir.actions.act_window',
            'domain': [('id', 'in', sata_ids.ids)],
        }

    def action_new_booking(self):
        action = self.env["ir.actions.actions"]._for_xml_id("custom_real_estate.book_unit_reservation_form_action")
        action['context'] = {
            'search_default_opportunity_id': self.id,
            'default_opportunity_id': self.id,
            'search_default_partner_id': self.partner_id.id,
            'default_partner_id': self.partner_id.id,
            'default_campaign_id': self.campaign_id.id,
            'default_medium_id': self.medium_id.id,
            'default_origin': self.name,
            'default_source_id': self.source_id.id,
            'default_company_id': self.company_id.id or self.env.company.id,
            'default_tag_ids': [(6, 0, self.tag_ids.ids)]}
        if self.user_id:
            action['context']['default_user_id'] = self.user_id.id
        return action

    def action_view_bookings(self):
        action = self.env["ir.actions.actions"]._for_xml_id("custom_real_estate.book_unit_reservation_tree_action")
        action['context'] = {
            'search_default_draft': 1,
            'search_default_partner_id': self.partner_id.id,
            'default_partner_id': self.partner_id.id,
            'default_opportunity_id': self.id, }
        action['domain'] = [('opportunity_id', '=', self.id), ('state', 'in', ['draft', 'confirmed'])]
        bookings = self.mapped('booking_ids').filtered(lambda l: l.state in ('draft', 'confirmed'))
        if len(bookings) == 1:
            action['views'] = [(self.env.ref('itsys_real_estate.unit_reservation_form_view').id, 'form')]
            action['res_id'] = bookings.id
        return action

    @api.depends('stage_id')
    def _compute_is_last(self):
        last_stage = self.env['crm.stage'].search([], order='sequence desc', limit=1)
        for rec in self:
            rec.is_last = not bool(last_stage and rec.stage_id == last_stage)

class UnitPrioritization(models.Model):
    _name = 'unit.prioritization'
    _description = 'Unit Prioritization'
    _rec_name = 'file_number'

    file_number = fields.Char(string="File Number")
    prioritization_number = fields.Char(string="Prioritization Number")
    opportunity_id = fields.Many2one('crm.lead')
    description = fields.Text('Description')
    customer = fields.Many2one('res.partner', related='opportunity_id.partner_id', store=True,
                                      string='Customer')

    @api.depends('file_number', 'prioritization_number')
    def _compute_number(self):
        for rec in self:
            if rec.file_number:
                rec.file_number_int = int(rec.file_number)
            else:
                rec.file_number_int = 0
            if rec.prioritization_number:
                rec.prioritization_number_int = int(rec.prioritization_number)
            else:
                rec.prioritization_number_int = 0

    file_number_int = fields.Integer(compute='_compute_number', store=True)
    prioritization_number_int = fields.Integer(compute='_compute_number', store=True)

    _name_unique = models.Constraint(
        ('unique(file_number)', 'The File Number must be unique!'),
        ('unique(prioritization_number)', 'The Prioritization Number must be unique!')
    )

    @api.depends('next_approval_id', 'next_approval_user_ids')
    def _compute_is_button(self):
        for rec in self:
            if self.env.user.id in rec.next_approval_user_ids.ids:
                rec.is_button = True
            else:
                rec.is_button = False

            if rec.next_approval_id.is_complete or rec.next_approval_id.is_reject:
                rec.is_button = False
            if rec.next_approval_id.is_last_approval:
                rec.is_last_level = True
            else:
                rec.is_last_level = False

    @api.depends('next_approval_id', 'next_approval_id.approval_user_ids')
    def _compute_next_approval_user_id(self):
        for rec in self:
            rec.next_approval_user_ids = [(6, 0, rec.next_approval_id.approval_user_ids.ids)]

    def _get_next_approval_id(self):
        rec = self.env['approval.level.prio'].search([('level', '=', 1)])
        return rec.id

    next_approval_id = fields.Many2one('approval.level.prio', string='Next Approval', tracking=True,
                                       default=_get_next_approval_id)
    next_approval_user_ids = fields.Many2many('res.users', string='Next Approval By',
                                              compute='_compute_next_approval_user_id', store=True)
    is_button = fields.Boolean('Is button', compute='_compute_is_button')
    is_last_level = fields.Boolean('Is button', compute='_compute_is_button')
    remark_ids = fields.One2many('remarks.approval.prio', 'lead_id', string='Remarks', tracking=True)

    def action_approve(self):
        view_id = self.env.ref('custom_real_estate.prio_remark_wizard_wizard_view').id
        return {'type': 'ir.actions.act_window',
                'name': _('Remarks'),
                'res_model': 'prio.remark.wizard',
                'target': 'new',
                'view_mode': 'form',
                'views': [[view_id, 'form']],
                }
