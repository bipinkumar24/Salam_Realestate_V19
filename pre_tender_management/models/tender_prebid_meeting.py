# -*- coding: utf-8 -*-
from odoo import fields, models


class TenderPrebidMeeting(models.Model):
    _name = 'tender.prebid.meeting'
    _description = 'Pre-Bid Meeting / Site Visit'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'meeting_date desc'

    name = fields.Char(required=True, default='Pre-Bid Meeting')
    opportunity_id = fields.Many2one(
        'crm.lead', string='Opportunity', required=True,
        ondelete='cascade', index=True,
    )
    meeting_type = fields.Selection([
        ('prebid', 'Pre-Bid Conference'),
        ('site_visit', 'Mandatory Site Visit'),
        ('clarification', 'Clarification Meeting'),
        ('client_engagement', 'Client Engagement'),
    ], default='prebid', required=True)
    is_mandatory = fields.Boolean(default=True)
    meeting_date = fields.Datetime(required=True, tracking=True)
    location = fields.Char()
    attendee_ids = fields.Many2many('res.users', string='Our Attendees')
    external_attendee_ids = fields.Many2many(
        'res.partner', string='External Attendees',
    )
    minutes = fields.Html(string='Minutes / AI Summary')
    action_item_ids = fields.One2many(
        'mail.activity', 'res_id', string='Action Items',
        domain=lambda self: [('res_model', '=', self._name)],
    )
    state = fields.Selection([
        ('planned', 'Planned'),
        ('attended', 'Attended'),
        ('missed', 'Missed'),
        ('cancelled', 'Cancelled'),
    ], default='planned', tracking=True)
    calendar_event_id = fields.Many2one('calendar.event', ondelete='set null')
    attachment_ids = fields.Many2many(
        'ir.attachment', 'tender_prebid_meeting_attachment_rel',
        'meeting_id', 'attachment_id', string='Attachments',
    )
