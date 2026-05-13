# -*- coding: utf-8 -*-
from odoo import fields, models, api, _
from odoo.exceptions import ValidationError
from datetime import datetime, time


class BookingLead(models.TransientModel):
    _name = 'booking.lead'
    _description = "Booking Lead"

    lead_type = fields.Selection(
        [('reservation', 'Reservation'), ('prioritization', 'Prioritization')], default='reservation',
        string='Type', required=1)

    def action_confirm(self):
        active_id = self.env.context.get('active_id')
        crm_lead_id = self.env['crm.lead'].browse(active_id)
        if self.lead_type == 'reservation':
            # action = self.env["ir.actions.actions"]._for_xml_id("custom_real_estate.book_unit_reservation_form_action")
            # action['context'] = {
            #     'search_default_opportunity_id': crm_lead_id.id,
            #     'default_opportunity_id': crm_lead_id.id,
            #     'search_default_partner_id': crm_lead_id.partner_id.id,
            #     'default_partner_id': crm_lead_id.partner_id.id,
            #     'default_campaign_id': crm_lead_id.campaign_id.id,
            #     'default_medium_id': crm_lead_id.medium_id.id,
            #     'default_origin': crm_lead_id.name,
            #     'default_source_id': crm_lead_id.source_id.id,
            #     'default_company_id': crm_lead_id.company_id.id or crm_lead_id.env.company.id,
            #     'default_tag_ids': [(6, 0, crm_lead_id.tag_ids.ids)]}
            # if crm_lead_id.user_id:
            #     action['context']['default_user_id'] = crm_lead_id.user_id.id
            # return action
            return {
                'name': 'Create Booking',
                'type': 'ir.actions.act_window',
                'view_mode': 'form',
                'res_model': 'crm.booking.wizard',
                'target': 'new',
                'context': {
                    'active_id': crm_lead_id.id,
                    'active_model': 'crm.lead',
                    'default_customer_id': crm_lead_id.partner_id.id,
                },
            }
        elif self.lead_type == 'prioritization':
            if crm_lead_id.booking_priority_count > 0:
                raise ValidationError(_('prioritization is already created!'))
            action = self.env["ir.actions.actions"]._for_xml_id("custom_real_estate.unit_prioritization_form_action")
            action['context'] = {
                'default_opportunity_id': crm_lead_id.id
            }
            return action
