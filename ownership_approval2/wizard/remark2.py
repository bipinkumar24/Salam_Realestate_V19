# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from datetime import datetime
import pytz
from odoo.exceptions import UserError, ValidationError


class Remark(models.TransientModel):
    _name = 'ownership.remark.wizard2'
    # _inherits = {'mail.compose.message': 'composer_id'}
    _description = "Real estate ownership contract approvals"

    @api.model
    def default_get(self, fields):
        result = super(Remark, self).default_get(fields)
        result['ownership_id_2'] = self._context.get('active_id')
        return result

    # ownership_id_2 = fields.Many2one('ownership.contract', string='Approval')
    name = fields.Text('Remarks')
    display_message = fields.Html(string='Display Message')
    is_first_level = fields.Boolean('Is First Level?')
    email_from = fields.Char('From Email')
    email_to = fields.Char('To Email')
    # composer_id = fields.Many2one('mail.compose.message', string='Composer', required=False)
    composer_id = fields.Many2one('mail.compose.message',string='Composer',required=False,ondelete='set null')
    attachment_ids = fields.Many2many('ir.attachment', 'remark2_attachment_id',
                                      'remark_id_2', 'attachment_id_2', string='Attachments')
    body_html = fields.Html('Body', translate=True, sanitize=False)
    is_send_email = fields.Boolean('Is Send Email')
    partner_ids = fields.Many2many('res.partner', string='Recipients')
    subject = fields.Char('Subject')
    body = fields.Html('Body')

    @api.onchange('ownership_id_2')
    def onchange_ownership_id(self):
        for rec in self:
            if rec.ownership_id_2:
                rec.display_message = self.ownership_id_2.next_approval_id_2.display_message
                if self.ownership_id_2.next_approval_id_2.level == 1:
                    rec.is_first_level = True
                else:
                    rec.is_first_level = False
                if self.ownership_id_2.next_approval_id_2.is_send_email and self.ownership_id_2.bbank == 'sab':
                    rec.is_send_email = True
                else:
                    rec.is_send_email = False

    def approve(self):
        level_rec = self.env['approval.level.ownership2'].search(
            [('level', '=', self.ownership_id_2.next_approval_id_2.level + 1)], limit=1)
        last_remark_id = self.env['remarks.approval.ownership2'].search(
            [('ownership_id_2', '=', self.ownership_id_2.id)],
            limit=1, order='create_date desc')

        consumed_hours = 0
        d2 = fields.Datetime.now()
        if last_remark_id:
            d1 = last_remark_id.remark_datettime
            diff = d2 - d1
            consumed_hours = diff

        if self.is_send_email:
            fetchmail_server_id = self.env['fetchmail.server'].search([])
            user = ''
            if fetchmail_server_id:
                user = fetchmail_server_id[0].user
            values = {'subject': self.subject,
                      'body_html': self.body,
                      'parent_id': None,
                      'email_from': self.env.user.email or None,
                      'auto_delete': False,
                      'recipient_ids': [(6, 0, self.partner_ids.ids)],
                      'reply_to': user,
                      'attachment_ids': [(6, 0, self.attachment_ids.ids)]
                      }
            result = self.env['mail.mail'].create(values).send()

        if not level_rec:
            raise UserError(_("Please Configure Approval Level First and Contact to Administrator"))

        self.ownership_id_2.remark2_ids = [(0, 0, {'name': self.name,
                                                   'user_id': self.env.user.id,
                                                   'remark_datettime': fields.Datetime.now(),
                                                   'consumed_hours': consumed_hours,
                                                   'from_stage_id_2': self.ownership_id_2.next_approval_id_2.id,
                                                   'to_stage_id_2': level_rec.id,
                                                   'remark_type': 'approve'
                                                   })]
        self.ownership_id_2.next_approval_id_2 = level_rec.id

    def previous(self):
        level_rec = self.env['approval.level.ownership2'].search(
            [('level', '=', self.ownership_id_2.next_approval_id_2.level - 1)],
            limit=1)
        last_remark_id = self.env['remarks.approval.ownership2'].search(
            [('ownership_id_2', '=', self.ownership_id_2.id)],
            limit=1,
            order='create_date desc')

        consumed_hours = 0
        d2 = fields.Datetime.now()
        if last_remark_id:
            d1 = last_remark_id.remark_datettime
            diff = d2 - d1
            consumed_hours = diff
        if not level_rec:
            raise UserError(_("Please Configure Approval Level First and Contact to Administrator"))
        self.ownership_id_2.remark2_ids = [(0, 0, {'name': self.name,
                                                   'user_id': self.env.user.id,
                                                   'remark_datettime': fields.Datetime.now(),
                                                   'consumed_hours': consumed_hours,
                                                   'from_stage_id_2': self.ownership_id_2.next_approval_id_2.id,
                                                   'to_stage_id_2': level_rec.id,
                                                   'remark_type': 'previous'
                                                   })]
        self.ownership_id_2.next_approval_id_2 = level_rec.id

    def reject(self):
        level_rec = self.env['approval.level.ownership2'].search([('is_reject', '=', True)], limit=1)
        if not level_rec:
            raise UserError(_("Please Configure Reject Level First or Contact to Administrator"))
        consumed_hours = 0
        last_remark_id = self.env['remarks.approval.ownership2'].search(
            [('ownership_id_2', '=', self.ownership_id_2.id)],
            limit=1,
            order='create_date desc')
        d2 = fields.Datetime.now()
        if last_remark_id:
            d1 = last_remark_id.remark_datettime
            diff = d2 - d1
            consumed_hours = diff
        self.ownership_id_2.remark2_ids = [(0, 0, {'name': self.name,
                                                   'user_id': self.env.user.id,
                                                   'remark_datettime': fields.Datetime.now(),
                                                   'consumed_hours': consumed_hours,
                                                   'from_stage_id_2': self.ownership_id_2.next_approval_id_2.id,
                                                   'to_stage_id_2': level_rec.id,
                                                   'remark_type': 'reject'
                                                   })]
        self.ownership_id_2.next_approval_id_2 = level_rec.id
