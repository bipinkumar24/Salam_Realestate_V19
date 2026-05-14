# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from datetime import datetime
import pytz
from odoo.exceptions import UserError, ValidationError


class Remark(models.TransientModel):
    _name = 'prio.remark.wizard'
    _inherits = {'mail.compose.message': 'composer_id'}
    _description = "CRM Lead"

    @api.model
    def default_get(self, fields):
        result = super(Remark, self).default_get(fields)
        result['lead_id'] = self._context.get('active_id')
        return result

    lead_id = fields.Many2one('unit.prioritization', string='Approval Refund')
    name = fields.Text('Remarks')
    display_message = fields.Html(string='Display Message')
    is_first_level = fields.Boolean('Is First Level?')
    is_final_level = fields.Boolean('Is Final Level?')
    email_from = fields.Char('From Email')
    email_to = fields.Char('To Email')
    composer_id = fields.Many2one(
        'mail.compose.message',
        string='Composer',
        required=True,
        ondelete='cascade',
        delegate=True,
    )
    attachment_ids = fields.Many2many('ir.attachment', 'pro_remark_attachment_id',
                                      'remark_id', 'attachment_id', string='Attachments')
    body_html = fields.Html('Body', translate=True, sanitize=False)
    is_send_email = fields.Boolean('Is Send Email')

    @api.onchange('lead_id')
    def onchange_lead_id(self):
        for rec in self:
            if rec.lead_id:
                rec.display_message = self.lead_id.next_approval_id.display_message
                if self.lead_id.next_approval_id.level == 1:
                    rec.is_first_level = True
                else:
                    rec.is_first_level = False
                    
                                   
    @api.onchange('lead_id')
    def onchange__the_lead_id(self):
        for rec in self:
            if rec.lead_id:
                if self.lead_id.next_approval_id.is_last_approval:
                    rec.is_final_level = True
                else:
                    rec.is_final_level = False
                          

    def approve(self):
        level_rec = self.env['approval.level.prio'].search([('level', '=', self.lead_id.next_approval_id.level + 1)], limit=1)

        last_remark_id = self.env['remarks.approval.prio'].search([('lead_id', '=', self.lead_id.id)], limit=1, order='create_date desc')

        consumed_hours = 0
        d2 = fields.Datetime.now()
        if last_remark_id:
            d1 = last_remark_id.remark_datettime
            diff = d2 - d1
            consumed_hours = diff


        if not level_rec:
            raise UserError(_("Please Configure Approval Level First and Contact to Administrator"))
        self.lead_id.remark_ids = [(0, 0, {'name': self.name,
                                           'user_id': self.env.user.id,
                                           'remark_datettime': fields.Datetime.now(),
                                           'consumed_hours': consumed_hours,
                                           'from_stage_id': self.lead_id.next_approval_id.id,
                                           'to_stage_id': level_rec.id,
                                           'remark_type': 'approve'
                                           })]
        self.lead_id.next_approval_id = level_rec.id

    def previous(self):
        level_rec = self.env['approval.level.prio'].search([('level', '=', self.lead_id.next_approval_id.level - 1)],
                                                          limit=1)
        last_remark_id = self.env['remarks.approval.prio'].search([('lead_id', '=', self.lead_id.id)], limit=1,
                                                                 order='create_date desc')

        consumed_hours = 0
        d2 = fields.Datetime.now()
        if last_remark_id:
            d1 = last_remark_id.remark_datettime
            diff = d2 - d1
            consumed_hours = diff
        if not level_rec:
            raise UserError(_("Please Configure Approval Level First and Contact to Administrator"))
        self.lead_id.remark_ids = [(0, 0, {'name': self.name,
                                           'user_id': self.env.user.id,
                                           'remark_datettime': fields.Datetime.now(),
                                           'consumed_hours': consumed_hours,
                                           'from_stage_id': self.lead_id.next_approval_id.id,
                                           'to_stage_id': level_rec.id,
                                           'remark_type': 'previous'
                                           })]
        self.lead_id.next_approval_id = level_rec.id

    def reject(self):
        level_rec = self.env['approval.level.prio'].search([('is_reject', '=', True)], limit=1)
        if not level_rec:
            raise UserError(_("Please Configure Reject Level First or Contact to Administrator"))
        consumed_hours = 0
        last_remark_id = self.env['remarks.approval.prio'].search([('lead_id', '=', self.lead_id.id)], limit=1,
                                                                 order='create_date desc')
        d2 = fields.Datetime.now()
        if last_remark_id:
            d1 = last_remark_id.remark_datettime
            diff = d2 - d1
            consumed_hours = diff
        self.lead_id.remark_ids = [(0, 0, {'name': self.name,
                                           'user_id': self.env.user.id,
                                           'remark_datettime': fields.Datetime.now(),
                                           'consumed_hours': consumed_hours,
                                           'from_stage_id': self.lead_id.next_approval_id.id,
                                           'to_stage_id': level_rec.id,
                                           'remark_type': 'reject'
                                           })]
        self.lead_id.next_approval_id = level_rec.id
        
    def complete(self):
        level_rec = self.env['approval.level.prio'].search([('is_complete', '=', True)], limit=1)
        if not level_rec:
            raise UserError(_("Please Configure Reject Level First or Contact to Administrator"))
        consumed_hours = 0
        last_remark_id = self.env['remarks.approval.prio'].search([('lead_id', '=', self.lead_id.id)], limit=1,
                                                                 order='create_date desc')
        d2 = fields.Datetime.now()
        if last_remark_id:
            d1 = last_remark_id.remark_datettime
            diff = d2 - d1
            consumed_hours = diff
        self.lead_id.remark_ids = [(0, 0, {'name': self.name,
                                           'user_id': self.env.user.id,
                                           'remark_datettime': fields.Datetime.now(),
                                           'consumed_hours': consumed_hours,
                                           'from_stage_id': self.lead_id.next_approval_id.id,
                                           'to_stage_id': level_rec.id,
                                           'remark_type': 'complete'
                                           })]
        self.lead_id.next_approval_id = level_rec.id    
        
        

