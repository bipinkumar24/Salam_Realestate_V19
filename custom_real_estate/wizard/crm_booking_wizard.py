# -*- coding: utf-8 -*-
from odoo import fields, api, models


class CrmBookingWizard(models.TransientModel):
    """Create Booking from CRM Lead"""
    _name = 'crm.booking.wizard'
    _description = 'Create Booking From CRM Lead'

    lead_id = fields.Many2one('crm.lead', string='Lead / Opportunity')
    customer_id = fields.Many2one('res.partner', string='Customer',
                                  domain="[('user_type','=','customer')]")
    property_id = fields.Many2one('property.details', string='Property')
    price = fields.Monetary(related="property_id.price")
    company_id = fields.Many2one('res.company', string='Company',
                                 default=lambda self: self.env.company)
    currency_id = fields.Many2one('res.currency', related='company_id.currency_id',
                                  string='Currency')
    book_price = fields.Monetary(string="Advance")
    ask_price = fields.Monetary(string="Customer Price")
    sale_price = fields.Monetary(related="property_id.sale_price", string="Sale Price")
    is_any_broker = fields.Boolean(string='Any Broker?')
    broker_id = fields.Many2one('res.partner', string='Broker',
                                domain=[('user_type', '=', 'broker')])
    commission_type = fields.Selection([('f', 'Fix'), ('p', 'Percentage')],
                                       string="Commission Type")
    broker_commission = fields.Monetary(string='Commission')
    broker_commission_percentage = fields.Float(string='Percentage')
    commission_from = fields.Selection([('customer', 'Customer'),
                                        ('landlord', 'Landlord',)],
                                       default='customer', string="Commission From")
    note = fields.Text(string="Note", translate=True)

    # Maintenance and utility Service
    is_any_maintenance = fields.Boolean(related="property_id.is_maintenance_service")
    total_maintenance = fields.Monetary(related="property_id.total_maintenance")
    is_utility_service = fields.Boolean(related="property_id.is_extra_service")
    total_service = fields.Monetary(related="property_id.extra_service_cost")

    # Booking Item
    booking_item_id = fields.Many2one('product.product', string="Booking Item")
    broker_item_id = fields.Many2one('product.product', string="Broker Item")

    # Penalty Details
    is_penalty_visible = fields.Boolean()
    is_penalty_applied = fields.Boolean(string="Is Any Penalty?")
    penalty_days_after_due = fields.Integer(
        string="Apply Penalty After (Days)",
        default=lambda self: self.env['ir.config_parameter'].sudo().get_param(
            'rental_management.penalty_days_after_due_for_sale_contract') or 5)
    penalty_percentage = fields.Integer(
        string="Percentage",
        default=lambda self: self.env['ir.config_parameter'].sudo().get_param(
            'rental_management.penalty_percentage_for_sale_contract') or 0)

    @api.model
    def default_get(self, fields_list):
        """Default Get"""
        res = super(CrmBookingWizard, self).default_get(fields_list)
        active_id = self._context.get('active_id')
        lead_id = self.env['crm.lead'].browse(active_id)
        default_broker_item = self.env['ir.config_parameter'].sudo().get_param(
            'rental_management.account_broker_item_id')
        default_deposit_item = self.env['ir.config_parameter'].sudo().get_param(
            'rental_management.account_deposit_item_id')
        res['lead_id'] = lead_id.id
        res['customer_id'] = lead_id.partner_id.id
        if lead_id.property_id:
            res['property_id'] = lead_id.property_id.id
        res['booking_item_id'] = int(
            default_deposit_item) if default_deposit_item else self.env.ref(
            'rental_management.property_product_2').id
        res['broker_item_id'] = int(default_broker_item) if default_broker_item else self.env.ref(
            'rental_management.property_product_3').id
        is_penalty_visible = self.env['ir.config_parameter'].sudo().get_param(
            'rental_management.is_penalty_applied')
        res['is_penalty_visible'] = is_penalty_visible
        return res

    def create_booking_action(self):
        """Process property booking from CRM Lead"""
        invoice_post_type = self.env['ir.config_parameter'].sudo().get_param(
            'rental_management.invoice_post_type')
        self.customer_id.user_type = 'customer'
        data = {
            'customer_id': self.customer_id.id,
            'property_id': self.property_id.id,
            'book_price': self.book_price * (-1),
            'ask_price': self.ask_price,
            'sale_price': self.ask_price,
            'is_any_broker': self.is_any_broker,
            'broker_id': self.broker_id.id,
            'commission_type': self.commission_type,
            'broker_commission': self.broker_commission,
            'broker_commission_percentage': self.broker_commission_percentage,
            'stage': 'booked',
            'commission_from': self.commission_from,
            'booking_item_id': self.booking_item_id.id,
            'broker_item_id': self.broker_item_id.id,
            'is_penalty_applied': self.is_penalty_applied,
            'penalty_days_after_due': self.penalty_days_after_due,
            'penalty_percentage': self.penalty_percentage,
            'lead_id': self.lead_id.id,
        }
        booking_id = self.env['property.vendor'].create(data)
        self.property_id.sold_booking_id = booking_id.id
        if self.lead_id:
            self.lead_id.property_id = self.property_id.id
        config_booking_property_mail_template = self.env['ir.config_parameter'].sudo().get_param(
            'rental_management.booking_mail_template_id')
        # if config_booking_property_mail_template:
        #     mail_template = self.env['mail.template'].browse(
        #         int(config_booking_property_mail_template))
        #     mail_template.send_mail(self.id,
        #                             email_values={'author_id': self.company_id.partner_id.id},
        #                             force_send=True)
        # else:
        #     mail_template = self.env.ref(
        #         'rental_management.property_book_mail_template_new', raise_if_not_found=False)
        #     if mail_template:
        #         mail_template.send_mail(self.id,
        #                                 email_values={'author_id': self.company_id.partner_id.id},
        #                                 force_send=True)

        if not booking_id.book_price == 0:
            record = {
                'product_id': self.booking_item_id.id,
                'name': 'Booked Amount of   ' + booking_id.property_id.name,
                'quantity': 1,
                'price_unit': self.book_price,
            }
            invoice_lines = [(0, 0, record)]
            data = {
                'partner_id': booking_id.customer_id.id,
                'move_type': 'out_invoice',
                'invoice_date': fields.Date.today(),
                'invoice_line_ids': invoice_lines,
            }
            book_invoice_id = self.env['account.move'].sudo().create(data)
            book_invoice_id.sold_id = booking_id.id
            if invoice_post_type == 'automatically':
                book_invoice_id.action_post()
            booking_id.book_invoice_id = book_invoice_id.id
            booking_id.book_invoice_state = True

        booking_id.property_id.stage = 'booked'
        booking_id.stage = 'booked'
        return {
            'type': 'ir.actions.act_window',
            'name': 'Property Booking',
            'res_model': 'property.vendor',
            'res_id': booking_id.id,
            'view_mode': 'form,list',
            'target': 'current',
        }

    @api.onchange('lead_id')
    def _onchange_lead_customer(self):
        """Set customer and note from lead"""
        for rec in self:
            if rec.lead_id:
                rec.customer_id = rec.lead_id.partner_id.id
                rec.note = rec.lead_id.description
