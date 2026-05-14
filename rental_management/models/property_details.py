# -*- coding: utf-8 -*-
import secrets
from PIL import Image as PILImage
import base64
import io
from odoo import api, fields, models, tools, _
from odoo.addons.html_editor.tools import get_video_embed_code
from odoo.exceptions import ValidationError


def is_float(str_vals):
    """Check if string is Float or not
    :param str_vals: String
    :return: True if string is Float or not
    """
    vals = str_vals.replace("-", "").replace(".", "").isnumeric()
    return bool(vals)


class PropertyDetails(models.Model):
    """Property Details"""
    _name = 'property.details'
    _description = 'Property Details and for registration new Property'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    # Property Details
    name = fields.Char(string='Name', required=True, translate=True)
    brocher_access_token = fields.Char('Access Token', copy=False)
    property_brochure_url = fields.Char('Brochure URL', compute="_compute_copy_property_brochure_url")
    image = fields.Binary(string='Image')
    type = fields.Selection([('land', 'Land'),
                             ('residential', 'Residential'),
                             ('commercial', 'Commercial'),
                             ('industrial', 'Industrial')
                             ], string='Property Type',
                            required=True,
                            default="residential")
    sale_lease = fields.Selection([('for_sale', 'Sale'),
                                   ('for_tenancy', 'Rent')],
                                  string='Property For',
                                  default='for_tenancy',
                                  required=True)
    property_seq = fields.Char(string='Property Code',
                               required=True,
                               readonly=False,
                               copy=False,
                               default=lambda self: '')
    stage = fields.Selection([('draft', 'Draft'),
                              ('available', 'Available'),
                              ('booked', 'In Booking'),
                              ('on_lease', 'On Rent'),
                              ('sale', 'In Sale'),
                              ('sold', 'Sold')],
                             group_expand='_expand_groups',
                             string='Status',
                             default='draft',
                             copy=False,
                             required=True)

    # Multi Companies
    company_id = fields.Many2one('res.company',
                                 string='Company',
                                 default=lambda self: self.env.company)
    currency_id = fields.Many2one('res.currency',
                                  related='company_id.currency_id',
                                  string='Currency')

    # Property Sub Type
    property_subtype_id = fields.Many2one('property.sub.type',
                                          string="Property Sub Type",
                                          domain="[('type','=',type)]")

    # Project & Sub Project & Region
    region_id = fields.Many2one('property.region', string="Region")
    property_project_id = fields.Many2one('property.project',
                                          string="Project")
    subproject_id = fields.Many2one('property.sub.project',
                                    string="Sub Project")

    # Address
    region_id = fields.Many2one('property.region', string="Region")
    zip = fields.Char(string='Zip')
    street = fields.Char(string='Street1', translate=True)
    street2 = fields.Char(string='Street2', translate=True)
    city = fields.Char(string='City  ', translate=True)
    city_id = fields.Many2one('property.res.city', string='City')
    country_id = fields.Many2one('res.country', 'Country')
    state_id = fields.Many2one(
        "res.country.state", string='State', store=True,
        domain="[('country_id', '=?', country_id)]")

    # Lat Long
    longitude = fields.Char(string='Longitude')
    latitude = fields.Char(string='Latitude')

    # Owner Details
    landlord_id = fields.Many2one('res.partner',
                                  string='LandLord',
                                  domain=[('user_type', '=', 'landlord')])
    landlord_phone = fields.Char(string="Phone", related="landlord_id.phone")
    landlord_email = fields.Char(string="Email", related="landlord_id.email")
    website = fields.Char(string='Website', translate=True)

    # Property Tags
    tag_ids = fields.Many2many('property.tag', string='Tags')

    # Availability
    amenities = fields.Boolean(string="Amenities")
    is_facilities = fields.Boolean(string="Specifications")
    is_images = fields.Boolean(string="Images")
    is_floor_plan = fields.Boolean(string="Floor Plans")
    nearby_connectivity = fields.Boolean(string="Nearby Connectivities")
    typology  = fields.Many2one('property.typology', string='Typology')
    zone = fields.Many2one('property.zone', string='Zone')
    lot = fields.Many2one('property.lot',     string='Lot')
    block = fields.Many2one('property.block',    string='Block')
    tf_no     = fields.Char(string='TF N#')
    property_sequence_no = fields.Char(
        string='Property ID',
        compute='_compute_property_sequence_no',
        store=True,
        help='Auto-generated as: Typology - Zone - Lot - Block - TF N#',
    )

    @api.depends('typology', 'zone', 'lot', 'block', 'tf_no')
    def _compute_property_sequence_no(self):
        for rec in self:
            parts = [
                rec.typology.name  if rec.typology  else '',
                rec.zone.name      if rec.zone      else '',
                rec.lot.name      if rec.lot      else '',
                rec.block.name     if rec.block     else '',
                rec.tf_no          or '',
            ]
            # Only include non-empty parts; join with " - "
            rec.property_sequence_no = ' - '.join(p for p in parts if p)
    # Area Measurement
    is_section_measurement = fields.Boolean(
        string="Is Section Area Measurement")
    measure_unit = fields.Selection([('sq_ft', 'ft²'),
                                     ('sq_m', 'm²'),
                                     ('sq_yd', 'yd²'),
                                     ('cu_ft', 'ft³'),
                                     ('cu_m', 'm³')],
                                    default='sq_ft',
                                    string="Area Measurement Unit")
    room_measurement_ids = fields.One2many('property.room.measurement',
                                           'room_measurement_id',
                                           string='Area Measurement')
    total_room_measure = fields.Integer(compute='compute_room_measure',
                                        store=True)
    total_area = fields.Float(string="Total Area")
    usable_area = fields.Float(string="Usable Area")
    sq_ft = fields.Float(string="Total Ft²")
    sq_m = fields.Float(string="Total M²")
    sq_yd = fields.Float(string="Total Yd²")
    cu_ft = fields.Float(string="Total Ft³")
    cu_m = fields.Float(string="Total M³")

    # Pricing
    price = fields.Monetary(string="Price")
    rent_unit = fields.Selection([('Day', "Day"),
                                  ('Month', "Month"),
                                  ('Year', "Year")],
                                 default='Month',
                                 string="Rent Unit")
    pricing_type = fields.Selection([('fixed', 'Fixed'),
                                     ('area_wise', 'Area Wise')],
                                    string="Pricing Type",
                                    default='fixed')
    price_per_area = fields.Monetary(string="Price / Area")

    # Utility Service
    is_extra_service = fields.Boolean(string="Utility Services")
    extra_service_ids = fields.One2many('extra.service.line',
                                        'property_id',
                                        string="Services")
    extra_service_cost = fields.Monetary(string="Utility Cost",
                                         compute="_compute_extra_service_cost")

    # Maintenance Service
    is_maintenance_service = fields.Boolean(string="Is Any Maintenance")
    maintenance_rent_type = fields.Selection([('once', 'Once'),
                                              ('recurring', 'Recurring')],
                                             string="Maintenance Type",
                                             default="once")
    maintenance_type = fields.Selection([('fixed', 'Fixed'),
                                         ('area_wise', 'Area Wise')],
                                        string="Charges Type")
    per_area_maintenance = fields.Monetary(string="Maintenance / Area")
    total_maintenance = fields.Monetary(string="Total Maintenance")

    #  Property Documents
    document_ids = fields.One2many('property.documents',
                                   'property_id',
                                   string="Documents")

    # Property Amities
    amenities_ids = fields.Many2many('property.amenities',
                                     string="Property Amenities")

    # Property Specification
    property_specification_ids = fields.Many2many('property.specification',
                                                  string='Property Specifications')

    # Image
    property_images_ids = fields.One2many('property.images',
                                          'property_id',
                                          string='Property Images')
    # Floor Plan
    floreplan_ids = fields.One2many('floor.plan',
                                    'property_id',
                                    string='Property Floor Plans')
    # Nearby Connectivity
    connectivity_ids = fields.One2many('property.connectivity.line',
                                       'property_id',
                                       string="Property Nearby Connectivity")

    # Maintenance History
    maintenance_ids = fields.One2many('maintenance.request',
                                      'property_id',
                                      string='Maintenance Histories')

    # Increment History
    increment_history_ids = fields.One2many('increment.history', 'property_id')

    # Property Broker And Tenancies
    tenancy_broker_count = fields.Integer(string="Rent Broker Count",
                                          compute="compute_count")
    tenancy_ids = fields.One2many('tenancy.details',
                                  'property_id',
                                  string='Rent Contracts')
    broker_ids = fields.One2many('tenancy.details',
                                 'property_id',
                                 string='Broker History',
                                 domain=[('is_any_broker', '=', True)])

    # Property Broker and Selling
    property_vendor_ids = fields.One2many('property.vendor',
                                          'property_id',
                                          string='Booking Details')
    sold_booking_id = fields.Many2one('property.vendor', copy=False,
                                      string="Booking")
    sale_broker_count = fields.Integer(string="Sale Broker Count",
                                       compute="compute_count")

    #  Enquiry
    tenancy_inquiry_ids = fields.One2many('tenancy.inquiry',
                                          'property_id',
                                          string="Rent Enquiry")
    sale_inquiry_ids = fields.One2many('sale.inquiry',
                                       'property_id',
                                       string="Sale Enquiry")

    # CRM Lead
    lead_count = fields.Integer(string="Lead Count",
                                compute="_compute_lead")
    lead_opp_count = fields.Integer(string="Opportunity Count",
                                    compute="_compute_lead")

    # Property Type wise Details
    total_floor = fields.Integer(string='No of Floors')
    floor = fields.Integer(string='Floor')
    bed = fields.Integer(string='Rooms', default=1)
    bathroom = fields.Integer(string='Bathrooms', default=1)
    parking = fields.Integer(string='Parking', default=1)
    facing = fields.Selection([('N', 'North(N)'),
                               ('E', 'East(E)'),
                               ('S', 'South(S)'),
                               ('W', 'West(W)'),
                               ('NE', 'North-East(NE)'),
                               ('SE', 'South-East(SE)'),
                               ('SW', 'South-West(SW)'),
                               ('NW', 'North-West(NW)'), ],
                              string='Facing', default='N')
    furnishing_id = fields.Many2one('property.furnishing', string="Furnishing")
    unit_type = fields.Integer(string="Unit Type", default=1)
    exposure_ids = fields.Many2many('property.exposure', string="Exposure/Orientation")

    # Smart Button Count
    document_count = fields.Integer(string='Document Count',
                                    compute='_compute_document_count')
    request_count = fields.Integer(string='Request Count',
                                   compute='_compute_request_count')
    booking_count = fields.Monetary(string='Booking Count',
                                    compute='_compute_booking_count')
    tenancy_count = fields.Integer(string='Rent Count',
                                   compute='_compute_booking_count')
    increment_history_count = fields.Integer(string="Increment History Count",
                                             compute="_compute_booking_count")
    vendor_count = fields.Integer(string="Sell Count", compute='_compute_booking_count')

    # DEPRECATED START--------------------------------------------------------------------------------------------------
    # Pricing
    token_amount = fields.Monetary(string='Book Price')
    sale_price = fields.Monetary(string='Sale Price')
    tenancy_price = fields.Monetary(string='Rent')
    # Property Details
    property_licence_no = fields.Char(string='License No.',
                                      translate=True)

    # Parent Property
    is_parent_property = fields.Boolean(string='Main Property')
    parent_property_id = fields.Many2one('parent.property')

    # Nearby Connectivity
    airport = fields.Char()
    national_highway = fields.Char()
    metro_station = fields.Char()
    metro_city = fields.Char()
    school = fields.Char()
    hospital = fields.Char()
    shopping_mall = fields.Char()
    park = fields.Char()
    # ---
    towers = fields.Boolean()
    no_of_towers = fields.Integer()
    facilities = fields.Text()
    # --
    parent_airport = fields.Char()
    parent_national_highway = fields.Char()
    parent_metro_station = fields.Char()
    parent_metro_city = fields.Char()
    parent_school = fields.Char()
    parent_hospital = fields.Char()
    parent_shopping_mall = fields.Char()
    parent_park = fields.Char()
    # --
    parent_zip = fields.Char()
    parent_street = fields.Char()
    parent_street2 = fields.Char()
    parent_city = fields.Char()
    parent_city_id = fields.Many2one(related='parent_property_id.city_id',
                                     string="Parent Cities")
    parent_country_id = fields.Many2one(related='parent_property_id.country_id',
                                        string="Parent Country")
    parent_state_id = fields.Many2one(related='parent_property_id.state_id',
                                      string="Parent State")
    parent_website = fields.Char()
    # --
    parent_amenities_ids = fields.Many2many(string="Parent Amentias",
                                            related='parent_property_id.amenities_ids')
    parent_specification_ids = fields.Many2many(string="Parent Specifications",
                                                related='parent_property_id.property_specification_ids')
    parent_landlord_id = fields.Many2one(string="Parent Landlord",
                                         related='parent_property_id.landlord_id')
    # --
    construct_year = fields.Char(string="Construct Year",
                                 size=4)
    buying_year = fields.Char()
    address = fields.Char()
    sold_invoice_id = fields.Many2one('account.move')
    sold_invoice_state = fields.Boolean()
    certificate_ids = fields.One2many('property.certificate',
                                      'property_id',
                                      string='Certificates')
    # --
    nearby_connectivity_ids = fields.Many2many('property.connectivity')
    room_no = fields.Char(string='Flat No./House No.')
    total_square_ft = fields.Char(string='Total Area Ft')
    usable_square_ft = fields.Char(string='Usable Area Ft')
    residence_type = fields.Selection([('apartment', 'Apartment'),
                                       ('bungalow', 'Bungalow'),
                                       ('vila', 'Vila'),
                                       ('raw_house', 'Raw House'),
                                       ('duplex', 'Duplex House'),
                                       ('single_studio', 'Single Studio')],
                                      string='Type of Residence')

    # Industrial
    industry_name = fields.Char()
    industry_location = fields.Selection([('inside', 'Inside City'),
                                          ('outside', 'Outside City')], )
    industrial_used_for = fields.Selection([('company', 'Company'),
                                            ('warehouses', 'Warehouses'),
                                            ('factories', 'Factories'),
                                            ('other', 'Other')])
    other_usages = fields.Char()
    industrial_facilities = fields.Text()
    # Land
    land_name = fields.Char()
    area_hector = fields.Char()
    land_facilities = fields.Text()
    # Commercial
    commercial_name = fields.Char()
    commercial_type = fields.Selection([('full_commercial', 'Full Commercial'),
                                        ('shops', 'Shops'),
                                        ('big_hall', 'Big Hall')])
    used_for = fields.Selection([('offices', 'Offices'),
                                 (' retail_stores', ' Retail Stores'),
                                 ('shopping_centres', 'Shopping Centres'),
                                 ('hotels', 'Hotels'),
                                 ('restaurants', 'Restaurants'),
                                 ('pubs', 'Pubs'),
                                 ('cafes', 'Cafes'),
                                 ('sport_facilities', 'Sport Facilities'),
                                 ('medical_centres', 'Medical Centres'),
                                 ('hospitals', 'Hospitals'),
                                 ('nursing_homes', 'Nursing Homes'),
                                 ('other', 'Other Use')
                                 ])
    floor_commercial = fields.Integer()
    total_floor_commercial = fields.Char()
    commercial_facilities = fields.Text()
    other_use = fields.Char()
    # Measurement
    commercial_measurement_ids = fields.One2many(
        'property.commercial.measurement', 'commercial_measurement_id')
    industrial_measurement_ids = fields.One2many(
        'property.industrial.measurement', 'industrial_measurement_id')
    total_commercial_measure = fields.Integer()
    total_industrial_measure = fields.Integer()
    furnishing = fields.Selection([('fully_furnished', 'Fully Furnished'),
                                   ('only_kitchen', 'Only Kitchen Furnished'),
                                   ('only_bed', 'Only BedRoom Furnished'),
                                   ('not_furnished', 'Not Furnished'),
                                   ], string='Furnishing Property', default='fully_furnished')

    # ----------------------------------------------------------------------------------------------------DEPRECATED END

    # Create, Constrain, Write, Scheduler, Name get
    # Create
    @api.model_create_multi
    def create(self, vals_list):
        """Property Create"""
        for vals in vals_list:
            if not vals.get('property_seq'):
                vals['property_seq'] = self.env['ir.sequence'].next_by_code(
                    'property.details') or ''
                vals['brocher_access_token'] = secrets.token_urlsafe(12)
        res = super(PropertyDetails, self).create(vals_list)
        return res

    # Stage Expand
    @api.model
    def _expand_groups(self, states, domain):
        return ['draft', 'available', 'booked', 'on_lease', 'sale', 'sold']

    # Unlink
    def unlink(self):
        for rec in self:
            if rec.stage in ['booked', 'on_lease', 'sale', 'sold']:
                raise ValidationError(
                    _("You can't delete property until status is in 'Draft' or 'Available'"))
            else:
                return super(PropertyDetails, self).unlink()

    # Name-get
    def name_get(self):
        """Name get for property title"""
        data = []
        for rec in self:
            if rec.type == 'land':
                data.append((rec.id, '%s - Land' % rec.name))
            elif rec.type == 'residential':
                data.append((rec.id, '%s - Residential' % rec.name))
            elif rec.type == 'commercial':
                data.append((rec.id, '%s - Commercial' % rec.name))
            elif rec.type == 'industrial':
                data.append((rec.id, '%s - Industrial' % rec.name))
        return data

    # Scheduler
    @api.model
    def update_property_address(self):
        """DEPRECATED : Update property address as per parent property"""
        properties = self.env['property.details'].search([('is_parent_property', '=', True),
                                                          ('parent_property_id', '!=', False)])
        for data in properties:
            data.onchange_parent_property_address()

    @api.model
    def update_property_measurement(self):
        """To Update measurement not required after vesrion 2.0"""
        pass
        # DEPRECATED

    # Compute
    # Total Measurement
    @api.depends('room_measurement_ids', 'type', 'measure_unit', 'is_section_measurement')
    def compute_room_measure(self):
        """Compute room measurement"""
        for rec in self:
            total = 0
            if rec.room_measurement_ids:
                for data in rec.room_measurement_ids:
                    total = total + data.carpet_area
            rec.total_room_measure = total
            if rec.is_section_measurement:
                rec.total_area = total

    # CRM Leads
    @api.depends('sale_lease')
    def _compute_lead(self):
        """Compute property lead"""
        for rec in self:
            rec.lead_count = self.env['crm.lead'].search_count(
                [('property_id', '=', rec.id), ('type', '=', 'lead')])
            rec.lead_opp_count = self.env['crm.lead'].search_count(
                [('property_id', '=', rec.id), ('type', '=', 'opportunity')])

    # Utility Service Total
    @api.depends('extra_service_ids')
    def _compute_extra_service_cost(self):
        """Compute extra service total cost"""
        for rec in self:
            amount = 0.0
            if rec.extra_service_ids:
                for data in rec.extra_service_ids:
                    amount = amount + data.price
            rec.extra_service_cost = amount

    # Counts
    # Document Count
    def _compute_document_count(self):
        """Compute property document count"""
        for rec in self:
            document_count = self.env['property.documents'].search_count(
                [('property_id', '=', rec.id)])
            rec.document_count = document_count

    # Booking Count
    def _compute_booking_count(self):
        """Compute property booking count"""
        for rec in self:
            booking = rec.sold_booking_id
            count = booking.book_price if booking.exists() else 0
            rec.booking_count = count
            rec.tenancy_count = self.env['tenancy.details'].search_count(
                [('property_id', '=', rec.id)])
            rec.increment_history_count = self.env['increment.history'].search_count(
                [('property_id', '=', rec.id)])
            rec.vendor_count = self.env['property.vendor'].search_count(
                [('property_id', '=', rec.id)])

    # Maintenance Request Count
    def _compute_request_count(self):
        """Compute maintenance request count"""
        for rec in self:
            request_count = self.env['maintenance.request'].search_count(
                [('property_id', '=', rec.id)])
            rec.request_count = request_count

    # Count
    def compute_count(self):
        """Compute sale & tenancy contract broker count"""
        for rec in self:
            rec.sale_broker_count = len(self.env['property.vendor'].sudo(
            ).search([('property_id', '=', rec.id), ('is_any_broker', '=', True)]).mapped(
                'broker_id').mapped('id'))
            rec.tenancy_broker_count = len(self.env['tenancy.details'].sudo(
            ).search([('property_id', '=', rec.id), ('is_any_broker', '=', True)]).mapped(
                'broker_id').mapped('id'))

    # Onchange
    # Area Wise Price
    @api.onchange('pricing_type', 'price_per_area', 'measure_unit', 'room_measurement_ids',
                  'is_section_measurement',
                  'total_area')
    def onchange_fix_area_price(self):
        """Onchange fix area price"""
        for rec in self:
            if rec.pricing_type == 'area_wise':
                rec.price = rec.total_area * rec.price_per_area

    # Maintenance Area wise Price
    @api.onchange('is_maintenance_service', 'maintenance_type', 'per_area_maintenance')
    def onchange_maintenance_type_charges(self):
        """Onchange maintenance type charge"""
        for rec in self:
            if rec.is_maintenance_service and rec.maintenance_type == 'area_wise':
                rec.total_maintenance = rec.per_area_maintenance * rec.total_area

    # Total Area
    @api.onchange('room_measurement_ids', 'is_section_measurement')
    def onchange_area_measure(self):
        """Onchange area measurement"""
        for rec in self:
            total = 0.0
            if rec.is_section_measurement and rec.room_measurement_ids:
                for data in rec.room_measurement_ids:
                    total = total + data.carpet_area
                rec.total_area = total

    # Property Sub Type Domain
    @api.onchange('type')
    def onchange_property_sub_type(self):
        """Onchange property sub type"""
        for rec in self:
            rec.property_subtype_id = False

    # State And Country Onchange
    @api.onchange('country_id')
    def _onchange_country_id(self):
        """Empty state_id onchange country_id"""
        if self.country_id and self.country_id != self.state_id.country_id:
            self.state_id = False

    @api.onchange('state_id')
    def _onchange_state(self):
        """Get country onchange state_id"""
        if self.state_id.country_id:
            self.country_id = self.state_id.country_id

    @api.constrains('total_area', 'usable_area', 'total_floor', 'bed', 'bathroom', 'parking', 'unit_type',
                    'price_per_area', 'price', 'per_area_maintenance', 'total_maintenance')
    def _check_values_is_not_negative(self):
        """Raise Validation if value is negative"""
        for rec in self:
            if rec.total_area and rec.total_area < 0:
                raise ValidationError(_("Total area must be zero or greater"))
            if rec.usable_area and rec.usable_area < 0:
                raise ValidationError(_("Usable area must be zero or greater"))
            if rec.total_floor and rec.total_floor < 0:
                raise ValidationError(_("No of floors must be zero or greater"))
            if rec.bed and rec.bed < 0:
                raise ValidationError(_("Rooms must be zero or greater"))
            if rec.bathroom and rec.bathroom < 0:
                raise ValidationError(_("Bathroom must be zero or greater"))
            if rec.parking and rec.parking < 0:
                raise ValidationError(_("Parking must be zero or greater"))
            if rec.unit_type and rec.unit_type < 0:
                raise ValidationError(_("BHK must be zero or greater"))

            if rec.price_per_area and rec.price_per_area < 0:
                raise ValidationError(_("Price / Area must be zero or greater"))
            if rec.price and rec.price < 0:
                if rec.sale_lease == 'for_sale':
                    raise ValidationError(_("Sale price must be zero or greater"))
                elif rec.sale_lease == 'for_tenancy':
                    raise ValidationError(_("Rent must be zero or greater"))
            if rec.per_area_maintenance and rec.per_area_maintenance < 0:
                raise ValidationError(_("Maintenance / Area must be zero or greater"))
            if rec.total_maintenance and rec.total_maintenance < 0:
                raise ValidationError(_("Total maintenance must be zero or greater"))

    @api.constrains('longitude', 'latitude')
    def _check_longitude_latitude_values(self):
        """
        Check longitude latitude values
        values should be float
        longitude should be between -180 to 180
        latitude should be between -80 to 80
        """
        for rec in self:
            if rec.longitude and not is_float(rec.longitude):
                raise ValidationError(
                    _("Longitude values must be float.")
                )
            if rec.latitude and not is_float(rec.latitude):
                raise ValidationError(
                    _("Latitude values must be float.")
                )
            if rec.longitude and is_float(rec.longitude) and (
                    float(rec.longitude) > 180 or float(rec.longitude) < -180):
                raise ValidationError(
                    _("Longitude must be in range of -180 to 180")
                )
            if rec.latitude and is_float(rec.latitude) and (
                    float(rec.latitude) > 90 or float(rec.latitude) < -90):
                raise ValidationError(
                    _("Latitude must be in range of -90 to 90")
                )

    # Buttons
    # Stage Buttons
    def action_in_available(self):
        """Status : Available"""
        for rec in self:
            rec.stage = 'available'

    def action_in_booked(self):
        """Status : Booked"""
        for rec in self:
            rec.stage = 'booked'

    def action_sold(self):
        """Status : Sold"""
        for rec in self:
            rec.stage = 'sold'

    def action_draft_property(self):
        """Status : Draft"""
        self.stage = "draft"

    def action_in_sale(self):
        """Status : Sale Property"""
        if self.sale_lease == 'for_sale':
            self.stage = 'sale'
        else:
            message = {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'type': 'info',
                    'title': 'You need to set "Price/Rent" to "For Sale" to proceed',
                    'sticky': False,
                }
            }
            return message

    # G-map Location
    def action_gmap_location(self):
        """Google map location bases on longitude and latitude"""
        if self.longitude and self.latitude:
            longitude = self.longitude
            latitude = self.latitude
            http_url = 'https://maps.google.com/maps?q=loc:' + latitude + ',' + longitude
            return {
                'type': 'ir.actions.act_url',
                'target': 'new',
                'url': http_url,
            }
        else:
            raise ValidationError(
                "! Enter Proper Longitude and Latitude Values")

    # Smart Button
    def action_maintenance_request(self):
        """View maintenance request"""
        return {
            'type': 'ir.actions.act_window',
            'name': 'Request',
            'res_model': 'maintenance.request',
            'domain': [('property_id', '=', self.id)],
            'context': {'default_property_id': self.id, 'create': False},
            'view_mode': 'kanban,tree,form',
            'target': 'current'
        }

    def action_property_document(self):
        """View property document"""
        return {
            'type': 'ir.actions.act_window',
            'name': 'Document',
            'res_model': 'property.documents',
            'domain': [('property_id', '=', self.id)],
            'context': {'default_property_id': self.id},
            'view_mode': 'tree',
            'target': 'current'
        }

    def action_sale_booking(self):
        """View Sale Booking"""
        return {
            'type': 'ir.actions.act_window',
            'name': 'Booking Information',
            'res_model': 'property.vendor',
            'domain': [('property_id', '=', self.id)],
            'context': {'default_property_id': self.id},
            'view_mode': 'tree,form',
            'target': 'current'
        }

    def action_crm_lead(self):
        """View CRM Lead"""
        return {
            'type': 'ir.actions.act_window',
            'name': 'Leads',
            'res_model': 'crm.lead',
            'domain': [('property_id', '=', self.id), ('type', '=', 'lead')],
            'context': {'default_property_id': self.id, 'default_type': 'lead'},
            'view_mode': 'tree,form',
            'target': 'current'
        }

    def action_crm_lead_opp(self):
        """View Lead opportunity"""
        return {
            'type': 'ir.actions.act_window',
            'name': 'Opportunity',
            'res_model': 'crm.lead',
            'domain': [('property_id', '=', self.id), ('type', '=', 'opportunity')],
            'context': {'default_property_id': self.id, 'default_type': 'opportunity'},
            'view_mode': 'tree,form',
            'target': 'current'
        }

    def action_view_contract(self):
        """View property rent contract"""
        return {
            'type': 'ir.actions.act_window',
            'name': 'Rent Contracts',
            'res_model': 'tenancy.details',
            'domain': [('property_id', '=', self.id)],
            'context': {'create': False},
            'view_mode': 'tree,form',
            'target': 'current'
        }

    def action_view_sell_contract(self):
        """View property sell contract"""
        return {
            'type': 'ir.actions.act_window',
            'name': 'Sell Contracts',
            'res_model': 'property.vendor',
            'domain': [('property_id', '=', self.id)],
            'context': {'create': False},
            'view_mode': 'list,form',
            'target': 'current'
        }

    def action_property_tenancy_broker(self):
        """View property tenancy broker"""
        ids = self.env['tenancy.details'].sudo().search(
            [('property_id', '=', self.id), ('is_any_broker', '=', True)]).mapped(
            'broker_id').mapped('id')
        return {
            'type': 'ir.actions.act_window',
            'name': 'Brokers',
            'res_model': 'res.partner',
            'domain': [('id', 'in', ids)],
            'context': {'create': False},
            'view_mode': 'tree,form',
            'target': 'current'
        }

    def action_property_sale_broker(self):
        """View property sale brokers"""
        ids = self.env['property.vendor'].sudo().search(
            [('property_id', '=', self.id), ('is_any_broker', '=', True)]).mapped(
            'broker_id').mapped('id')
        return {
            'type': 'ir.actions.act_window',
            'name': 'Brokers',
            'res_model': 'res.partner',
            'domain': [('id', 'in', ids)],
            'context': {'create': False},
            'view_mode': 'tree,form',
            'target': 'current'
        }

    def action_view_increment_history(self):
        """View rent increment history"""
        return {
            'type': 'ir.actions.act_window',
            'name': 'Increment History',
            'res_model': 'increment.history',
            'domain': [('property_id', '=', self.id)],
            'context': {'create': False},
            'view_mode': 'tree,form',
            'target': 'current'
        }

    # Server Action
    def action_available_property(self):
        """Status : Available property"""
        active_ids = self._context.get('active_ids')
        property_rec = self.env['property.details'].sudo().browse(active_ids)
        for data in property_rec:
            if data.stage == 'draft':
                data.write({
                    'stage': 'available'
                })

    # DashBoard
    @api.model
    def get_property_stats(self):
        """Get dashboard statics"""
        company_domain = [('company_id', 'in', self.env.companies.ids)]
        # Property Stages
        property = self.env['property.details']
        avail_property = property.sudo().search_count(
            [('stage', '=', 'available')] + company_domain)
        booked_property = property.sudo().search_count(
            [('stage', '=', 'booked')] + company_domain)
        lease_property = property.sudo().search_count(
            [('stage', '=', 'on_lease')] + company_domain)
        sale_property = property.sudo().search_count([('stage', '=', 'sale')] + company_domain)
        sold_property = property.sudo().search_count([('stage', '=', 'sold')] + company_domain)
        currency_symbol = self.env.company.currency_id.symbol
        land_property = property.sudo().search_count([('type', '=', 'land')] + company_domain)
        residential_property = property.sudo().search_count(
            [('type', '=', 'residential')] + company_domain)
        commercial_property = property.sudo().search_count(
            [('type', '=', 'commercial')] + company_domain)
        industrial_property = property.sudo().search_count(
            [('type', '=', 'industrial')] + company_domain)
        property_type = [['Land', 'Residential', 'Commercial', 'Industrial'],
                         [land_property, residential_property, commercial_property,
                          industrial_property]]
        property_stage = [
            ['Available Properties', 'Sold Properties', 'Booked Properties', 'On Sale', 'On Lease'],
            [avail_property, sold_property, booked_property, sale_property, lease_property]]

        # Rent Contract
        rent_contract = self.env['tenancy.details'].sudo()
        draft_contract = rent_contract.search_count(
            [('contract_type', '=', 'new_contract')] + company_domain)
        running_contract = rent_contract.search_count(
            [('contract_type', '=', 'running_contract')] + company_domain)
        expire_contract = rent_contract.search_count(
            [('contract_type', '=', 'expire_contract')] + company_domain)
        extend_contract = rent_contract.search_count(
            [('is_extended', '=', True)] + company_domain)
        close_contract = rent_contract.search_count(
            [('contract_type', '=', 'close_contract')] + company_domain)
        full_tenancy_total = sum(self.env['rent.invoice'].search(
            ['|', ('type', '=', 'rent'), ('type', '=', 'full_rent')] + company_domain).mapped(
            'rent_invoice_id').mapped(
            'amount_total'))
        pending_invoice = self.env['rent.invoice'].search_count(
            [('payment_state', '=', 'not_paid')] + company_domain)

        # Sale Contract
        sale_contract = self.env['property.vendor'].sudo()
        booked = sale_contract.search_count([('stage', '=', 'booked')] + company_domain)
        sale_sold = sale_contract.search_count([('stage', '=', 'sold')] + company_domain)
        refund = sale_contract.search_count([('stage', '=', 'refund')] + company_domain)
        sold_total = sum(
            sale_contract.search([('stage', '=', 'sold')] + company_domain).mapped('sale_price'))
        pending_invoice_sale = self.env['account.move'].search_count(
            [('sold_id', '!=', False), ('payment_state', '=', 'not_paid')] + company_domain)

        # Region, Project, Sub Project, Properties
        region_count = self.env['property.region'].search_count([])
        project_count = self.env['property.project'].search_count(company_domain)
        subproject_count = self.env['property.sub.project'].search_count(company_domain)
        total_property = property.search_count(company_domain)

        # Customer & Landlord
        customer_count = self.env['res.partner'].sudo(
        ).search_count([('user_type', '=', 'customer')])
        landlord_count = self.env['res.partner'].sudo(
        ).search_count([('user_type', '=', 'landlord')])

        return {
            # Property
            'avail_property': avail_property,
            'booked_property': booked_property,
            'lease_property': lease_property,
            'sale_property': sale_property,
            'sold_property': sold_property,
            # Rent Contract
            'draft_contract': draft_contract,
            'running_contract': running_contract,
            'expire_contract': expire_contract,
            'extend_contract': extend_contract,
            'close_contract': close_contract,
            'pending_invoice': pending_invoice,
            'rent_total': str(
                round(full_tenancy_total, 2)) + ' ' + currency_symbol if currency_symbol else "",
            # Sale Contract
            'booked': booked,
            'sale_sold': sale_sold,
            'refund': refund,
            'sold_total': str(
                round(sold_total, 2)) + ' ' + currency_symbol if currency_symbol else "",
            'pending_invoice_sale': pending_invoice_sale,
            # Customer & Landlord
            'customer_count': customer_count,
            'landlord_count': landlord_count,
            # Region, Project, Sub Project, Properties
            'region_count': region_count,
            'project_count': project_count,
            'subproject_count': subproject_count,
            'total_property': total_property,
            # Graph
            'property_type': property_type,
            'property_stage': property_stage,
            'due_paid_amount': self.due_paid_amount(),
            'tenancy_top_broker': self.get_top_broker(),
        }

    @api.model
    def retrieve_list_dashboard_data(self):
        """ This function returns the values to populate the custom dashboard in
            the Property List views.
        """
        property_obj = self.env['property.details']
        company_domain = [('company_id', 'in', self.env.companies.ids)]

        stages = ['available', 'booked', 'on_lease', 'sale', 'sold', 'draft']
        data = {}

        for stage in stages:
            data[f'{stage}_prop_count'] = property_obj.search_count([('stage', '=', stage)] + company_domain)
            data[f'{stage}_land_prop_count'] = property_obj.search_count([
                ('stage', '=', stage),
                ('type', '=', 'land'),
            ] + company_domain)
            data[f'{stage}_residential_prop_count'] = property_obj.search_count([
                ('stage', '=', stage),
                ('type', '=', 'residential'),
            ] + company_domain)
            data[f'{stage}_commercial_prop_count'] = property_obj.search_count([
                ('stage', '=', stage),
                ('type', '=', 'commercial'),
            ] + company_domain)
            data[f'{stage}_industrial_prop_count'] = property_obj.search_count([
                ('stage', '=', stage),
                ('type', '=', 'industrial'),
            ] + company_domain)

        data['total_prop_count'] = property_obj.search_count(company_domain)
        data['total_land_prop_count'] = property_obj.search_count([
            ('type', '=', 'land'),
        ] + company_domain)
        data['total_residential_prop_count'] = property_obj.search_count([
            ('type', '=', 'residential'),
        ] + company_domain)
        data['total_commercial_prop_count'] = property_obj.search_count([
            ('type', '=', 'commercial'),
        ] + company_domain)
        data['total_industrial_prop_count'] = property_obj.search_count([
            ('type', '=', 'industrial'),
        ] + company_domain)
        # FOR RENT
        for_rent_domain = [('stage', '=', 'available'), ('sale_lease', '=', 'for_tenancy')] + company_domain
        data['total_for_rent_count'] = property_obj.search_count(for_rent_domain)
        data['total_for_rent_land_count'] = property_obj.search_count(
            for_rent_domain + [('type', '=', 'land')])
        data['total_for_rent_residential_count'] = property_obj.search_count(
            for_rent_domain + [('type', '=', 'residential')])
        data['total_for_rent_commercial_count'] = property_obj.search_count(
            for_rent_domain + [('type', '=', 'commercial')])
        data['total_for_rent_industrial_count'] = property_obj.search_count(
            for_rent_domain + [('type', '=', 'industrial')])
        return data

    def get_top_broker(self):
        """Dashboard : Get top broker"""
        company_ids = self.env.companies.ids
        broker_tenancy = {}
        broker_sold = {}
        for group in self.env['tenancy.details'].read_group(
                [('is_any_broker', '=', True), ('company_id', 'in', company_ids)],
                ['broker_id'],
                ['broker_id'], limit=5):
            if group['broker_id']:
                name = self.env['res.partner'].sudo().browse(
                    int(group['broker_id'][0])).name
                broker_tenancy[name] = group['broker_id_count']
        for group in self.env['property.vendor'].read_group(
                [('is_any_broker', '=', True), ('company_id', 'in', company_ids),
                 ('stage', '=', 'sold')],
                ['broker_id'],
                ['broker_id'], limit=5):
            if group['broker_id']:
                name = self.env['res.partner'].sudo().browse(
                    int(group['broker_id'][0])).name
                broker_sold[name] = group['broker_id_count']

        brokers_tenancy_list = dict(
            sorted(broker_tenancy.items(), key=lambda x: x[1], reverse=True))
        broker_sold_list = dict(
            sorted(broker_sold.items(), key=lambda x: x[1], reverse=True))
        return [list(brokers_tenancy_list.keys()), list(brokers_tenancy_list.values()),
                list(broker_sold_list.keys()),
                list(broker_sold_list.values())]

    def due_paid_amount(self):
        """Dashboard : Due / Paid Amount"""
        company_domain = [('company_id', 'in', self.env.companies.ids)]
        sold = {}
        tenancy = {}
        not_paid_amount_sold = 0.0
        paid_amount_sold = 0.0
        not_paid_amount_tenancy = 0.0
        paid_amount_tenancy = 0.0
        property_sold = self.env['account.move'].sudo().search(
            [('sold_id', '!=', False)] + company_domain)
        for data in property_sold:
            if data.sold_id.stage == "sold":
                if data.payment_state == "not_paid":
                    not_paid_amount_sold = not_paid_amount_sold + data.amount_total
                if data.payment_state == "paid":
                    paid_amount_sold = paid_amount_sold + data.amount_total
        sold['Due'] = not_paid_amount_sold
        sold['Paid'] = paid_amount_sold
        property_tenancy = self.env['rent.invoice'].sudo().search(company_domain)
        for rec in property_tenancy:
            if rec.payment_state == 'not_paid':
                not_paid_amount_tenancy = not_paid_amount_tenancy + rec.rent_invoice_id.amount_total
            if rec.payment_state == 'paid':
                paid_amount_tenancy = paid_amount_tenancy + rec.rent_invoice_id.amount_total
        tenancy['Due'] = not_paid_amount_tenancy
        tenancy['Paid'] = paid_amount_tenancy
        return [list(sold.keys()), list(sold.values()), list(tenancy.keys()),
                list(tenancy.values())]

    # Deprecated Compute / Onchange / Methods START-------------------------------------
    @api.depends('commercial_measurement_ids', 'type', 'measure_unit')
    def compute_commercial_measure(self):
        for rec in self:
            total = 0
            sq_ft = 0
            sq_m = 0
            sq_yd = 0
            cu_ft = 0
            cu_m = 0
            if rec.commercial_measurement_ids:
                for data in rec.commercial_measurement_ids:
                    total = total + data.carpet_area
                    sq_ft = sq_ft + data.sq_ft
                    sq_m = sq_m + data.sq_m
                    sq_yd = sq_yd + data.sq_yd
                    cu_ft = cu_ft + data.cu_ft
                    cu_m = cu_m + data.cu_m
            rec.total_commercial_measure = total
            if rec.type == 'commercial':
                rec.sq_ft = sq_ft
                rec.sq_m = sq_m
                rec.sq_yd = sq_yd
                rec.cu_ft = cu_ft
                rec.cu_m = cu_m

    @api.depends('industrial_measurement_ids', 'type', 'measure_unit')
    def compute_industrial_measure(self):
        for rec in self:
            total = 0
            sq_ft = 0
            sq_m = 0
            sq_yd = 0
            cu_ft = 0
            cu_m = 0
            if rec.industrial_measurement_ids:
                for data in rec.industrial_measurement_ids:
                    total = total + data.carpet_area
                    sq_ft = sq_ft + data.sq_ft
                    sq_m = sq_m + data.sq_m
                    sq_yd = sq_yd + data.sq_yd
                    cu_ft = cu_ft + data.cu_ft
                    cu_m = cu_m + data.cu_m
            rec.total_industrial_measure = total
            if rec.type == 'industrial':
                rec.sq_ft = sq_ft
                rec.sq_m = sq_m
                rec.sq_yd = sq_yd
                rec.cu_ft = cu_ft
                rec.cu_m = cu_m

    @api.onchange('is_parent_property', 'parent_property_id')
    def _onchange_parent_property_type(self):
        for rec in self:
            if not rec.is_parent_property and not rec.parent_property_id:
                return
            rec.type = rec.parent_property_id.type
            rec.residence_type = rec.parent_property_id.residence_type
            rec.total_floor = rec.parent_property_id.total_floor
            rec.towers = rec.parent_property_id.towers
            rec.no_of_towers = rec.parent_property_id.no_of_towers
            rec.industry_location = rec.parent_property_id.industry_location
            rec.commercial_type = rec.parent_property_id.commercial_type

    @api.onchange('is_parent_property', 'parent_property_id')
    def onchange_parent_property_address(self):
        for rec in self:
            if rec.is_parent_property and rec.parent_property_id:
                rec.landlord_id = rec.parent_property_id.landlord_id.id
                rec.zip = rec.parent_property_id.zip
                rec.street = rec.parent_property_id.street
                rec.street2 = rec.parent_property_id.street2
                rec.city_id = rec.parent_property_id.city_id.id
                rec.country_id = rec.parent_property_id.country_id.id
                rec.state_id = rec.parent_property_id.state_id.id
                rec.website = rec.parent_property_id.website

    # --------------------------------------------------------------------Deprecated Compute / Onchange / Methods END

    def get_report_color(self):
        """Fetch the report color from system settings"""
        color = self.env['ir.config_parameter'].get_param('rental_management.report_color_config')
        if not color:
            color = self.env.company.primary_color or '#714B67'
        return color


    @api.depends('brocher_access_token')
    def _compute_copy_property_brochure_url(self):
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        for rec in self:
            if rec.brocher_access_token:
                self.property_brochure_url = f"{base_url}/property-brochure/{rec.brocher_access_token}"
            else:
                self.property_brochure_url = ""

    def property_brochure_detail_mail_template(self):
        mail_template = self.env.ref(
            'rental_management.property_brochure_details_mail_template',
            raise_if_not_found=False
        )

        if not mail_template:
            raise ValidationError(_('Property Detail: Property Brochure Details Mail Template not found.'))

        ctx = {
            "default_model": "property.details",
            "default_use_template": True,
            "default_email_from": self.company_id.email or self.env.user.email,
            "default_template_id": mail_template.id,
            "subject": (_('Property Brochure Detail')),
            "force_email": True,
            'property_brochure_link': f"/property-brochure/{self.brocher_access_token}"

        }

        return {
            "name": "Property Brochure Details",
            "type": "ir.actions.act_window",
            "res_model": "mail.compose.message",
            "view_mode": "form",
            "target": "new",
            "context": ctx,
        }

    @api.model
    def property_brochure_url_cron(self):
        """Property Brochure Details Cron"""
        properties = self.env['property.details'].search([('brocher_access_token', '=', False)])
        for rec in properties:
            rec['brocher_access_token'] = secrets.token_urlsafe(12)
            self._compute_copy_property_brochure_url()


# Area Measurement
class PropertyRoomMeasurement(models.Model):
    """Property Measurement"""
    _name = 'property.room.measurement'
    _description = 'Room Property Measurement Details'

    type_room = fields.Selection([('hall', 'Hall'),
                                  ('bed_room', 'Bed Room'),
                                  ('kitchen', 'Kitchen'),
                                  ('drawing_room', 'Drawing Room'),
                                  ('bathroom', 'Bathroom'),
                                  ('store_room', 'Store Room'),
                                  ('balcony', 'Balcony'),
                                  ('wash_area', 'Wash Area'), ],
                                 string='House Section')
    section_id = fields.Many2one('property.area.type', string="Section")
    length = fields.Integer(string='Length')
    width = fields.Integer(string='Width')
    height = fields.Integer(string='Height', default=1)
    no_of_unit = fields.Integer(string="No of Unit", default=1)
    carpet_area = fields.Integer(string='Total Area',
                                 compute='_compute_carpet_area')
    measure = fields.Char(string='ft²',
                          default='ft²',
                          readonly=True,
                          translate=True)
    room_measurement_id = fields.Many2one('property.details',
                                          string='Room Details')
    measure_unit = fields.Selection(related="room_measurement_id.measure_unit",
                                    store=True)
    sq_ft = fields.Float(string="Total Square Feet")
    sq_m = fields.Float(string="Total Square Meters")
    sq_yd = fields.Float(string="Total Square Yards")
    cu_ft = fields.Float(string="Total Cubic Feet")
    cu_m = fields.Float(string="Total Cubic Meters")

    @api.depends('length', 'width', 'height', 'measure_unit', 'no_of_unit')
    def _compute_carpet_area(self):
        """Compute total carpet area"""
        for rec in self:
            total = 0.0
            if rec.measure_unit in ['sq_ft', 'sq_m', 'sq_yd']:
                total = rec.length * rec.width * rec.no_of_unit
            elif rec.measure_unit in ['cu_ft', 'cu_m']:
                total = rec.length * rec.width * rec.height * rec.no_of_unit
            rec.carpet_area = total


# Property Documents
class PropertyDocuments(models.Model):
    """Property Documents"""
    _name = 'property.documents'
    _description = 'Document related to Property'
    _rec_name = 'doc_type'

    property_id = fields.Many2one('property.details',
                                  string='Property Name',
                                  readonly=True)
    document_date = fields.Date(string='Date', default=fields.Date.today())
    doc_type = fields.Selection([('photos', 'Photo'),
                                 ('brochure', 'Brochure'),
                                 ('certificate', 'Certificate'),
                                 ('insurance_certificate',
                                  'Insurance Certificate'),
                                 ('utilities_insurance', 'Utilities Certificate')],
                                string='Document Type', required=True)
    document = fields.Binary(string='Documents', required=True)
    file_name = fields.Char(string='File Name', translate=True)


# Property Amentias
class PropertyAmenities(models.Model):
    """Property Amenities"""
    _name = 'property.amenities'
    _description = 'Details About Property Amenities'
    _rec_name = 'title'

    sequence = fields.Integer()
    image = fields.Binary(string='Image')
    title = fields.Char(string='Title', translate=True)

    @api.constrains('title')
    def _check_name_is_unique(self):
        """Raise validation if name is not unique"""
        for rec in self:
            amenity_name = self.search([('id', '!=', rec.id)]).mapped('title')
            if rec.title and rec.title in amenity_name:
                raise ValidationError(_("A record with this title already exists. Please choose a different title."))


# Property Specification
class PropertySpecification(models.Model):
    """Property Specification"""
    _name = 'property.specification'
    _description = 'Details About Property Specification'
    _rec_name = 'title'

    image = fields.Image(string='Image')
    title = fields.Char(string='Title', translate=True)
    description = fields.Text(string="Description", translate=True)
    description_line1 = fields.Char(string='Description ', translate=True)
    description_line2 = fields.Char(string='Description Line 2',
                                    translate=True)
    description_line3 = fields.Char(string='Description Line 3',
                                    translate=True)

    @api.constrains('title')
    def _check_name_is_unique(self):
        """Raise validation if name is not unique"""
        for rec in self:
            cities_name = self.search([('id', '!=', rec.id)]).mapped('title')
            if rec.title and rec.title in cities_name:
                raise ValidationError(_("A record with this title already exists. Please choose a different title."))


# Property Floor Plan
class FloorPlan(models.Model):
    """Property Flore Plans"""
    _name = 'floor.plan'
    _description = 'Details About Floor Plan'
    _inherit = ["image.mixin"]
    _order = "sequence, id"

    title = fields.Char(string='Title', translate=True)
    sequence = fields.Integer(default=10)
    property_id = fields.Many2one('property.details', string='Property')
    image = fields.Image(string='Image ')
    video_url = fields.Char("Video URL",
                            help="URL of a video for showcasing your property.")
    embed_code = fields.Html(compute="_compute_embed_code",
                             sanitize=False)
    can_image_1024_be_zoomed = fields.Boolean(string="Can Image 1024 be zoomed",
                                              compute="_compute_can_image_1024_be_zoomed",
                                              store=True)

    # @api.depends("image", "image_1024")
    # def _compute_can_image_1024_be_zoomed(self):
    #     """Compute image can be zoomed or  not"""
    #     for image in self:
    #         image.can_image_1024_be_zoomed = image.image and tools.is_image_size_above(image.image,
    #                                                                                    image.image_1024)
    @api.depends("image", "image_1024")
    def _compute_can_image_1024_be_zoomed(self):
        """Compute image can be zoomed or not"""
        for image in self:
            if image.image and image.image_1024:
                orig = PILImage.open(io.BytesIO(base64.b64decode(image.image))).size
                resized = PILImage.open(io.BytesIO(base64.b64decode(image.image_1024))).size
                image.can_image_1024_be_zoomed = orig[0] > resized[0] or orig[1] > resized[1]
            else:
                image.can_image_1024_be_zoomed = False

    @api.depends("video_url")
    def _compute_embed_code(self):
        """Compute embed code"""
        for image in self:
            image.embed_code = get_video_embed_code(image.video_url) or False

    @api.constrains("video_url")
    def _check_valid_video_url(self):
        """Check video url is valid or not"""
        for image in self:
            if image.video_url and not image.embed_code:
                raise ValidationError(_("Provided video URL for '%s' is not valid. "
                                        "Please enter a valid video URL.", image.name, ))


# Property Images
class PropertyImages(models.Model):
    _name = 'property.images'
    _description = 'Property Images'
    _inherit = ["image.mixin"]
    _order = "sequence, id"

    title = fields.Char(string='Title', translate=True)
    sequence = fields.Integer(default=10)
    property_id = fields.Many2one('property.details',
                                  string='Property Name',
                                  readonly=True)
    image = fields.Image(string='Images')
    video_url = fields.Char("Video URL",
                            help="URL of a video for showcasing your property.")
    embed_code = fields.Html(compute="_compute_embed_code",
                             sanitize=False)
    can_image_1024_be_zoomed = fields.Boolean(string="Can Image 1024 be zoomed",
                                              compute="_compute_can_image_1024_be_zoomed",
                                              store=True)

    # @api.depends("image", "image_1024")
    # def _compute_can_image_1024_be_zoomed(self):
    #     """Compute image can be zoomed or not"""
    #     for image in self:
    #         image.can_image_1024_be_zoomed = image.image and tools.is_image_size_above(image.image,
    #                                                                                    image.image_1024)
    @api.depends("image", "image_1024")
    def _compute_can_image_1024_be_zoomed(self):
        """Compute image can be zoomed or not"""
        for image in self:
            if image.image and image.image_1024:
                orig = PILImage.open(io.BytesIO(base64.b64decode(image.image))).size
                resized = PILImage.open(io.BytesIO(base64.b64decode(image.image_1024))).size
                image.can_image_1024_be_zoomed = orig[0] > resized[0] or orig[1] > resized[1]
            else:
                image.can_image_1024_be_zoomed = False

    @api.depends("video_url")
    def _compute_embed_code(self):
        """Compute embed code"""
        for image in self:
            image.embed_code = get_video_embed_code(image.video_url) or False

    @api.constrains("video_url")
    def _check_valid_video_url(self):
        """Check video url is valid or not"""
        for image in self:
            if image.video_url and not image.embed_code:
                raise ValidationError(_("Provided video URL for '%s' is not valid."
                                        " Please enter a valid video URL.",
                                        image.name, ))


# Property Tags
class PropertyTag(models.Model):
    _name = 'property.tag'
    _description = 'Property Tags'
    _rec_name = 'title'

    title = fields.Char(string='Title', translate=True)
    color = fields.Integer(string='Color')

    @api.constrains('title')
    def _check_name_is_unique(self):
        """Raise validation if name is not unique"""
        for rec in self:
            tag_name = self.search([('id', '!=', rec.id)]).mapped('title')
            if rec.title and rec.title in tag_name:
                raise ValidationError(_("A record with this title already exists. Please choose a different title."))


# Utility Service
class TenancyExtraService(models.Model):
    """Extra Service Product"""
    _inherit = 'product.product'

    is_extra_service_product = fields.Boolean(string="Is Extras Service")


# Utility Service Line
class ExtraServiceLine(models.Model):
    """Extra Service Line"""
    _name = 'extra.service.line'
    _description = "Tenancy Extras Service"

    service_id = fields.Many2one('product.product',
                                 string="Service",
                                 domain=[('is_extra_service_product', '=', True)])
    price = fields.Float(string="Cost")
    service_type = fields.Selection([('once', 'Once'),
                                     ('monthly', 'Recurring')],
                                    string="Type",
                                    default="once")
    property_id = fields.Many2one('property.details',
                                  string="Property")

    @api.constrains('price')
    def _check_price_is_not_negative(self):
        """Raise validation if price is negative"""
        for rec in self:
            if rec.price and rec.price < 0:
                raise ValidationError(_("Cost must be zero or greater"))

    @api.onchange('service_id')
    def _onchange_service_id_price(self):
        """Service price bases product"""
        for rec in self:
            if rec.service_id:
                rec.price = rec.service_id.lst_price


# City
class PropertyResCity(models.Model):
    """Res City"""
    _name = 'property.res.city'
    _description = 'Cities'

    color = fields.Integer('Color')
    name = fields.Char(string="City Name", required=True, translate=True)

    @api.constrains('name')
    def _check_name_is_unique(self):
        """Raise validation if name is not unique"""
        for rec in self:
            cities_name = self.search([('id', '!=', rec.id)]).mapped('name')
            if rec.name and rec.name in cities_name:
                raise ValidationError(_("A record with this name already exists. Please choose a different name."))


# Property Connectivity
class PropertyConnectivity(models.Model):
    """Property Connectivity"""
    _name = 'property.connectivity'
    _description = "Property Nearby Connectivity"

    name = fields.Char(string="Title", translate=True)
    distance = fields.Char(string="Distance", translate=True)
    image = fields.Image(string='Images')

    @api.constrains('name')
    def _check_name_is_unique(self):
        """Raise validation if name is not unique"""
        for rec in self:
            connectivity_name = self.search([('id', '!=', rec.id)]).mapped('name')
            if rec.name and rec.name in connectivity_name:
                raise ValidationError(_("A record with this title already exists. Please choose a different title."))


# Property Connectivity Line
class PropertyConnectivityLine(models.Model):
    """Property Connectivity Line"""
    _name = 'property.connectivity.line'
    _description = "Property Connectivity Line"

    property_id = fields.Many2one('property.details')
    connectivity_id = fields.Many2one('property.connectivity',
                                      string="Nearby Connectivity")
    name = fields.Char(string="Name", translate=True)
    image = fields.Image(related="connectivity_id.image", string='Images')
    distance = fields.Char(string="Distance", translate=True)


# Tenancy Inquiry
class TenancyInquiry(models.Model):
    """Rent Inquiry Leas"""
    _name = 'tenancy.inquiry'
    _description = "Rent Inquiry"
    _rec_name = 'lead_id'

    property_id = fields.Many2one('property.details',
                                  string="Property Details")
    note = fields.Text(string="Note", translate=True)
    duration_id = fields.Many2one('contract.duration', string='Duration')
    customer_id = fields.Many2one('res.partner', string="Customer")
    lead_id = fields.Many2one('crm.lead', string="Lead")

    def name_get(self):
        """Name get"""
        data = []
        for rec in self:
            if rec.lead_id:
                data.append((rec.id, '%s - %s' %
                             (rec.customer_id.name, rec.lead_id.name)))
            else:
                data.append((rec.id, '%s' % rec.customer_id.name))
        return data


# Sale Inquiry
class SaleInquiry(models.Model):
    """Sale Inquiry Lead"""
    _name = 'sale.inquiry'
    _description = "Sale Inquiry"
    _rec_name = 'lead_id'

    property_id = fields.Many2one('property.details',
                                  string="Property Details")
    note = fields.Text(string="Note", translate=True)
    company_id = fields.Many2one('res.company',
                                 string='Company',
                                 default=lambda self: self.env.company)
    currency_id = fields.Many2one('res.currency',
                                  related='company_id.currency_id',
                                  string='Currency')
    ask_price = fields.Monetary(string="Ask Price")
    customer_id = fields.Many2one('res.partner',
                                  string="Customer")
    lead_id = fields.Many2one('crm.lead',
                              string="Lead")

    def name_get(self):
        """Name get"""
        data = []
        for rec in self:
            if rec.lead_id:
                data.append((rec.id, '%s - %s' %
                             (rec.customer_id.name, rec.lead_id.name)))
            else:
                data.append((rec.id, '%s' % rec.customer_id.name))
        return data


# Property Area Type
class PropertyAreaType(models.Model):
    """Property area types"""
    _name = 'property.area.type'
    _description = "Property Area Type"

    name = fields.Char(string="Title")
    type = fields.Selection([('room', 'Rooms'),
                             ('bathroom', 'Bathrooms'),
                             ('parking', 'Parking'),
                             ('hall', 'Hall'),
                             ('kitchen', 'Kitchen'),
                             ('other', 'Other')], string="Type")

    @api.constrains('name')
    def _check_name_is_unique(self):
        """Raise validation if name is not unique"""
        for rec in self:
            cities_name = self.search([('id', '!=', rec.id)]).mapped('name')
            if rec.name and rec.name in cities_name:
                raise ValidationError(_("A record with this title already exists. Please choose a different title."))


# Property Sub Type
class PropertySubType(models.Model):
    """Property subtype"""
    _name = 'property.sub.type'
    _description = "Property Sub Type"

    name = fields.Char(string="Title")
    type = fields.Selection([('land', 'Land'),
                             ('residential', 'Residential'),
                             ('commercial', 'Commercial'),
                             ('industrial', 'Industrial')],
                            string="Type")
    sequence = fields.Integer()
    is_apartment = fields.Boolean(
        string='Is Apartment (Floor-based)',
        default=False,
        help='Tick for apartment subtypes. '
             'When ticked, the Create Units wizard will require floor numbers. '
             'Leave unticked for villas, bungalows, houses, etc. — '
             'units will be created without floor numbers.')

    @api.constrains('name')
    def _check_name_is_unique(self):
        """Raise validation if name is not unique"""
        for rec in self:
            cities_name = self.search([('id', '!=', rec.id)]).mapped('name')
            if rec.name and rec.name in cities_name:
                raise ValidationError(_("A record with this title already exists. Please choose a different title."))


# Furnishing Type
class PropertyFurnishing(models.Model):
    """Property Furnishing"""
    _name = 'property.furnishing'
    _description = "Property Furnishing"

    name = fields.Char(string="Title")

    @api.constrains('name')
    def _check_name_is_unique(self):
        """Raise validation if name is not unique"""
        for rec in self:
            cities_name = self.search([('id', '!=', rec.id)]).mapped('name')
            if rec.name and rec.name in cities_name:
                raise ValidationError(_("A record with this title already exists. Please choose a different title."))


# Increment history
class IncrementHistory(models.Model):
    """Increment History"""
    _name = 'increment.history'
    _description = "Increment History"
    _rec_name = "contract_ref"

    property_id = fields.Many2one('property.details', string="Property")
    date = fields.Date(string="Date", default=fields.Date.today())
    company_id = fields.Many2one('res.company', string='Company',
                                 default=lambda self: self.env.company)
    currency_id = fields.Many2one('res.currency', related='company_id.currency_id',
                                  string='Currency')
    contract_ref = fields.Char(string="Contract Ref.")
    rent_type = fields.Selection([('fixed', 'Fixed'), ('area_wise', 'Area Wise')],
                                 string="Pricing Type")
    rent_increment_type = fields.Selection([('fix', 'Fix Amount'), ('percentage', 'Percentage')],
                                           string="Increment Type", default="fix")
    increment_percentage = fields.Float(string="Increment(%)", default=1)
    increment_amount = fields.Monetary(string="Increment Amount")
    previous_rent = fields.Monetary(string="Previous Rent")
    incremented_rent = fields.Monetary(string="Final Rent")


# Property Exposure
class PropertyExposure(models.Model):
    """Property Exposure"""
    _name = 'property.exposure'
    _description = __doc__

    name = fields.Char(string="Title")


# DEPRECATED MODEL START---------------------------------------------------------------------------------------
class PropertyCommercialMeasurement(models.Model):
    """Commercial Measurement"""
    _name = 'property.commercial.measurement'
    _description = 'Commercial Property Measurement Details'

    shops = fields.Char(string='Section', translate=True)
    length = fields.Integer(string='Length')
    width = fields.Integer(string='Width')
    height = fields.Integer(string='Height')
    carpet_area = fields.Integer(string='Area', compute='_compute_carpet_area')
    measure = fields.Char(string='ft²', default='ft²',
                          readonly=True, translate=True)
    commercial_measurement_id = fields.Many2one(
        'property.details', string='Commercial Details')
    no_of_unit = fields.Integer(string="No of Unit", default=1)
    measure_unit = fields.Selection(
        related="commercial_measurement_id.measure_unit", store=True)
    sq_ft = fields.Float(string="Total Square Feet",
                         compute='_compute_carpet_area')
    sq_m = fields.Float(string="Total Square Meters",
                        compute='_compute_carpet_area')
    sq_yd = fields.Float(string="Total Square Yards",
                         compute='_compute_carpet_area')
    cu_ft = fields.Float(string="Total Cubic Feet",
                         compute='_compute_carpet_area')
    cu_m = fields.Float(string="Total Cubic Meters",
                        compute='_compute_carpet_area')

    @api.depends('length', 'width', 'height', 'measure_unit', 'no_of_unit')
    def _compute_carpet_area(self):
        """Compute carpaet area"""
        for rec in self:
            total = 0
            sq_ft = 0
            sq_m = 0
            sq_yd = 0
            cu_ft = 0
            cu_m = 0
            if rec.length and rec.width:
                total = rec.length * rec.width * rec.no_of_unit
            if rec.measure_unit == 'sq_ft':
                sq_ft = total
                sq_m = total * 0.092903
                sq_yd = total * 0.111111
                cu_ft = total * rec.height
                cu_m = cu_ft * 0.0283168
            elif rec.measure_unit == 'sq_m':
                sq_ft = total * 10.764
                sq_m = total
                sq_yd = total * 1.19599
                cu_ft = total * rec.height * 35.3147
                cu_m = total * rec.height
            elif rec.measure_unit == 'sq_yd':
                sq_ft = total * 9
                sq_m = total * 0.836127
                sq_yd = total
                cu_ft = total * rec.height * 27
                cu_m = cu_ft / 35.3147
            elif rec.measure_unit == 'cu_ft' and rec.height > 0:
                cu_ft = total * rec.height
                sq_ft = cu_ft / rec.height
                sq_m = (cu_ft / rec.height) * 0.092903
                sq_yd = cu_ft / (rec.height / 3)
                cu_m = cu_ft * 0.0283168
            elif rec.measure_unit == 'cu_m' and rec.height > 0:
                cu_m = total * rec.height
                sq_ft = (cu_m / rec.height) * 10.764
                sq_m = cu_m / rec.height
                sq_yd = (cu_m / 1.0) / (rec.height * 1.0936)
                cu_ft = cu_m * 35.315
            rec.carpet_area = total
            rec.sq_ft = sq_ft
            rec.sq_m = sq_m
            rec.sq_yd = sq_yd
            rec.cu_ft = cu_ft
            rec.cu_m = cu_m


class PropertyIndustrialMeasurement(models.Model):
    """Industrial Measurement"""
    _name = 'property.industrial.measurement'
    _description = 'Industrial Property Measurement Details'

    asset = fields.Char(string='industrial Asset', translate=True)
    length = fields.Integer(string='Length')
    width = fields.Integer(string='Width')
    height = fields.Integer(string='Height')
    carpet_area = fields.Integer(string='Area', compute='_compute_carpet_area')
    measure = fields.Char(string='ft²', default='ft²',
                          readonly=True, translate=True)
    industrial_measurement_id = fields.Many2one(
        'property.details', string='Industrial Details')
    no_of_unit = fields.Integer(string="No of Unit", default=1)
    measure_unit = fields.Selection(
        related="industrial_measurement_id.measure_unit", store=True)
    sq_ft = fields.Float(string="Total Square Feet",
                         compute='_compute_carpet_area')
    sq_m = fields.Float(string="Total Square Meters",
                        compute='_compute_carpet_area')
    sq_yd = fields.Float(string="Total Square Yards",
                         compute='_compute_carpet_area')
    cu_ft = fields.Float(string="Total Cubic Feet",
                         compute='_compute_carpet_area')
    cu_m = fields.Float(string="Total Cubic Meters",
                        compute='_compute_carpet_area')

    @api.depends('length', 'width', 'height', 'measure_unit', 'no_of_unit')
    def _compute_carpet_area(self):
        for rec in self:
            total = 0
            sq_ft = 0
            sq_m = 0
            sq_yd = 0
            cu_ft = 0
            cu_m = 0
            if rec.length and rec.width:
                total = rec.length * rec.width * rec.no_of_unit
            if rec.measure_unit == 'sq_ft':
                sq_ft = total
                sq_m = total * 0.092903
                sq_yd = total * 0.111111
                cu_ft = total * rec.height
                cu_m = cu_ft * 0.0283168
            elif rec.measure_unit == 'sq_m':
                sq_ft = total * 10.764
                sq_m = total
                sq_yd = total * 1.19599
                cu_ft = total * rec.height * 35.3147
                cu_m = total * rec.height
            elif rec.measure_unit == 'sq_yd':
                sq_ft = total * 9
                sq_m = total * 0.836127
                sq_yd = total
                cu_ft = total * rec.height * 27
                cu_m = cu_ft / 35.3147
            elif rec.measure_unit == 'cu_ft' and rec.height > 0:
                cu_ft = total * rec.height
                sq_ft = cu_ft / rec.height
                sq_m = (cu_ft / rec.height) * 0.092903
                sq_yd = cu_ft / (rec.height / 3)
                cu_m = cu_ft * 0.0283168
            elif rec.measure_unit == 'cu_m' and rec.height > 0:
                cu_m = total * rec.height
                sq_ft = (cu_m / rec.height) * 10.764
                sq_m = cu_m / rec.height
                sq_yd = (cu_m / 1.0) / (rec.height * 1.0936)
                cu_ft = cu_m * 35.315
            rec.carpet_area = total
            rec.sq_ft = sq_ft
            rec.sq_m = sq_m
            rec.sq_yd = sq_yd
            rec.cu_ft = cu_ft
            rec.cu_m = cu_m


class CertificateType(models.Model):
    """Certificate Types"""
    _name = 'certificate.type'
    _description = 'Type Of Certificate'
    _rec_name = 'type'

    type = fields.Char(string='Type', translate=True)


class PropertyCertificate(models.Model):
    """Property Certificate"""
    _name = 'property.certificate'
    _description = 'Property Related All Certificate'
    _rec_name = 'type_id'

    type_id = fields.Many2one('certificate.type', string='Type')
    expiry_date = fields.Date(string='Expiry Date')
    responsible = fields.Char(string='Responsible', translate=True)
    note = fields.Char(string='Note', translate=True)
    property_id = fields.Many2one('property.details', string='Property')


class ParentProperty(models.Model):
    """Parent Property"""
    _name = 'parent.property'
    _description = 'Parent Property Details'

    name = fields.Char(string='Name', translate=True)
    image = fields.Binary(string='Image')
    company_id = fields.Many2one('res.company',
                                 string='Company',
                                 default=lambda self: self.env.company)
    amenities_ids = fields.Many2many('property.amenities', string='Amenities')
    property_specification_ids = fields.Many2many('property.specification',
                                                  string='Specification')
    zip = fields.Char(string='Zip')
    street = fields.Char(string='Street1', translate=True)
    street2 = fields.Char(string='Street2', translate=True)
    city = fields.Char(string='City ', translate=True)
    city_id = fields.Many2one('property.res.city', string='City')
    country_id = fields.Many2one('res.country', 'Country')
    state_id = fields.Many2one("res.country.state",
                               string='State',
                               readonly=False, store=True,
                               domain="[('country_id', '=?', country_id)]")
    landlord_id = fields.Many2one('res.partner', string='LandLord', domain=[
        ('user_type', '=', 'landlord')])
    website = fields.Char(string='Website', translate=True)
    airport = fields.Char(string='Airport')
    national_highway = fields.Char(string='National Highway', translate=True)
    metro_station = fields.Char(string='Metro Station', translate=True)
    metro_city = fields.Char(string='Metro City', translate=True)
    school = fields.Char(string="School", translate=True)
    hospital = fields.Char(string="Hospital", translate=True)
    shopping_mall = fields.Char(string="Mall", translate=True)
    park = fields.Char(string="Park", translate=True)
    nearby_connectivity_ids = fields.Many2many('property.connectivity',
                                               string="Nearby Connectivity ")
    type = fields.Selection([('residential', 'Residential'),
                             ('commercial', 'Commercial'),
                             ('industrial', 'Industrial')],
                            string='Property Type',
                            default="residential")
    property_count = fields.Integer(string="Property Count",
                                    compute="_compute_properties")

    # Residential
    residence_type = fields.Selection([('apartment', 'Apartment'),
                                       ('bungalow', 'Bungalow'),
                                       ('vila', 'Vila'),
                                       ('raw_house', 'Raw House'),
                                       ('duplex', 'Duplex House'),
                                       ('single_studio', 'Single Studio')],
                                      string='Type of Residence')
    total_floor = fields.Integer(string='Total Floor')
    towers = fields.Boolean(string='Tower Building')
    no_of_towers = fields.Integer(string='No. of Towers')

    # Commercial
    commercial_type = fields.Selection([('full_commercial', 'Full Commercial'),
                                        ('shops', 'Shops'),
                                        ('big_hall', 'Big Hall')],
                                       string='Commercial Type')

    # Industrial
    industry_location = fields.Selection([('inside', 'Inside City'),
                                          ('outside', 'Outside City')],
                                         string='Location')

    def _compute_properties(self):
        """Compute properties count"""
        for rec in self:
            rec.property_count = self.env['property.details'].search_count(
                [('parent_property_id', '=', rec.id), ('is_parent_property', '=', True)])

    def action_properties_parent(self):
        """View associated properties"""
        return {
            'type': 'ir.actions.act_window',
            'name': 'Properties',
            'res_model': 'property.details',
            'domain': [('parent_property_id', '=', self.id), ('is_parent_property', '=', True)],
            'context': {'default_parent_property_id': self.id, 'default_is_parent_property': True},
            'view_mode': 'kanban,tree,form',
            'target': 'current'
        }
# ------------------------------------------------------------------------------------------DEPRECATED MODEL END

# ── Property Classification Models ────────────────────────────────────────────


class PropertyTypology(models.Model):
    """Property Typology"""
    _name = 'property.typology'
    _description = 'Property Typology'
    _order = 'name'

    name = fields.Char(string='Typology', required=True)
    active = fields.Boolean(default=True)

    _name_unique = models.Constraint(
        ('unique(name)', 'Sector name must be unique!.'),
    )

class PropertyZone(models.Model):
    """Property Zone"""
    _name = 'property.zone'
    _description = 'Property Zone'
    _order = 'name'

    name = fields.Char(string='Zone', required=True)
    active = fields.Boolean(default=True)

    _name_unique = models.Constraint(
        ('unique(name)', 'Zone name must be unique!'),
    )

class PropertyLot(models.Model):
    """Property Plot"""
    _name = 'property.lot'
    _description = 'Property Plot'
    _order = 'name'

    name = fields.Char(string='Lot', required=True)
    active = fields.Boolean(default=True)

    _name_unique = models.Constraint(
        ('unique(name)', 'Lot name must be unique!'),
    )

class PropertyBlock(models.Model):
    """Property Block"""
    _name = 'property.block'
    _description = 'Property Block'
    _order = 'name'

    name = fields.Char(string='Block', required=True)
    active = fields.Boolean(default=True)

    _name_unique = models.Constraint(
        ('unique(name)', 'Block name must be unique'),
    )
