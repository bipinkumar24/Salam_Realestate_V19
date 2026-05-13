# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class Remark(models.TransientModel):
    _name = 'account.remark.wizard'
    _inherits = {'mail.compose.message': 'composer_id'}
    _description = "Account Move"

    @api.model
    def default_get(self, fields_list):
        result = super().default_get(fields_list)
        result['move_id'] = self._context.get('active_id')
        return result

    move_id = fields.Many2one('account.move', string='Approval Refund')
    name = fields.Text('Remarks')
    display_message = fields.Html(string='Display Message')
    is_first_level = fields.Boolean('Is First Level?')
    email_from = fields.Char('From Email')
    email_to = fields.Char('To Email')
    composer_id = fields.Many2one(
        'mail.compose.message',
        string='Composer',
        required=True,
        ondelete='cascade',
        delegate=True,
    )
    attachment_ids = fields.Many2many('ir.attachment', 'remarks_attachment_id',
                                      'remark_id', 'attachment_id', string='Attachments')
    body_html = fields.Html('Body', render_engine='qweb', translate=True, sanitize=False)
    is_send_email = fields.Boolean('Is Send Email')

    @api.onchange('move_id')
    def onchange_move_id(self):
        for rec in self:
            customer_ids = []
            if rec.move_id:
                rec.display_message = rec.move_id.next_approval_id.display_message
                if rec.move_id.next_approval_id.level == 1:
                    rec.is_first_level = True
                else:
                    rec.is_first_level = False
                if rec.move_id.next_approval_id.is_send_email:
                    rec.is_send_email = True
                    next_number = rec.move_id.next_approval_id.level + 1
                    level_rec = self.env['approval.level.account'].search([('level', '=', next_number)], limit=1)
                    if level_rec:
                        user_ids = level_rec.approval_user_ids
                        for user in user_ids:
                            if user.partner_id:
                                if user.partner_id.email:
                                    customer_ids.append(user.partner_id.id)
                    rec.partner_ids = [(6, 0, customer_ids)]
                    if rec.move_id.next_approval_id.email_template_id:
                        rec.body = rec.move_id.next_approval_id.email_template_id.body_html
                        rec.subject = rec.move_id.next_approval_id.email_template_id.subject
                        rec.attachment_ids = [(6, 0, rec.move_id.next_approval_id.email_template_id.attachment_ids.ids)]
                else:
                    rec.is_send_email = False

    def approve(self):
        if self.move_id.next_approval_id.level == 2:
            level_rec = self.env['approval.level.account'].search(
                [('level', '=', self.move_id.next_approval_id.level + 2)], limit=1)
        else:
            level_rec = self.env['approval.level.account'].search([('level', '=', self.move_id.next_approval_id.level + 1)], limit=1)


        last_remark_id = self.env['remarks.approval.account'].search([('move_id', '=', self.move_id.id)], limit=1, order='create_date desc')

        consumed_hours = 0
        d2 = fields.Datetime.now()
        if last_remark_id:
            d1 = last_remark_id.remark_datettime
            diff = d2 - d1
            consumed_hours = diff

        if not level_rec:
            raise UserError(_("Please Configure Approval Level First and Contact to Administrator"))
        self.move_id.remark_ids = [(0, 0, {'name': self.name,
                                           'user_id': self.env.user.id,
                                           'remark_datettime': fields.Datetime.now(),
                                           'consumed_hours': consumed_hours,
                                           'from_stage_id': self.move_id.next_approval_id.id,
                                           'to_stage_id': level_rec.id,
                                           'remark_type': 'approve'
                                           })]
        if self.is_send_email:
            values = {'subject': self.subject,
                      'body_html': self.body,
                      'email_from': self.env.user.email or None,
                      'auto_delete': False,
                      'recipient_ids': [(6, 0, self.partner_ids.ids)],
                      'attachment_ids': [(6, 0, self.attachment_ids.ids)]
                    }
            result = self.env['mail.mail'].create(values).send()
        self.move_id.next_approval_id = level_rec.id

    def previous(self):
        level_rec = self.env['approval.level.account'].search([('level', '=', self.move_id.next_approval_id.level - 1)],
                                                          limit=1)
        last_remark_id = self.env['remarks.approval.account'].search([('move_id', '=', self.move_id.id)], limit=1,
                                                                 order='create_date desc')

        consumed_hours = 0
        d2 = fields.Datetime.now()
        if last_remark_id:
            d1 = last_remark_id.remark_datettime
            diff = d2 - d1
            consumed_hours = diff
        if not level_rec:
            raise UserError(_("Please Configure Approval Level First and Contact to Administrator"))
        self.move_id.remark_ids = [(0, 0, {'name': self.name,
                                           'user_id': self.env.user.id,
                                           'remark_datettime': fields.Datetime.now(),
                                           'consumed_hours': consumed_hours,
                                           'from_stage_id': self.move_id.next_approval_id.id,
                                           'to_stage_id': level_rec.id,
                                           'remark_type': 'previous'
                                           })]
        self.move_id.next_approval_id = level_rec.id

    def reject(self):
        level_rec = self.env['approval.level.account'].search([('is_reject', '=', True)], limit=1)
        if not level_rec:
            raise UserError(_("Please Configure Reject Level First or Contact to Administrator"))
        consumed_hours = 0
        last_remark_id = self.env['remarks.approval.account'].search([('move_id', '=', self.move_id.id)], limit=1,
                                                                 order='create_date desc')
        d2 = fields.Datetime.now()
        if last_remark_id:
            d1 = last_remark_id.remark_datettime
            diff = d2 - d1
            consumed_hours = diff
        self.move_id.remark_ids = [(0, 0, {'name': self.name,
                                           'user_id': self.env.user.id,
                                           'remark_datettime': fields.Datetime.now(),
                                           'consumed_hours': consumed_hours,
                                           'from_stage_id': self.move_id.next_approval_id.id,
                                           'to_stage_id': level_rec.id,
                                           'remark_type': 'reject'
                                           })]
        self.move_id.next_approval_id = level_rec.id
