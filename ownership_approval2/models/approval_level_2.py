# -*- coding: utf-8 -*-

from odoo import api, models, fields, _


class ApprovalLevel(models.Model):
    _name = 'approval.level.ownership2'
    _description = 'Approval Level CRM'
    _order = 'level'

    name = fields.Char('Name')
    display_message = fields.Html('Display Message')
    level = fields.Integer('Level')
    is_last_approval = fields.Boolean('Is Last')
    is_reject = fields.Boolean('Is Reject')
    approval_user_ids = fields.Many2many('res.users', string='Approval User')
    group_ids = fields.Many2many('res.groups', 'res_groups_approval_rel', 'approval_id', 'group_id',
                                 string='Groups')
    is_prior_doc_required = fields.Boolean('doc 1')
    is_res_doc_required = fields.Boolean('doc 2')
    is_sell_doc_required = fields.Boolean('doc 3')
    is_final_doc_required = fields.Boolean('doc 4')
    is_customer_doc_required = fields.Boolean('Is Customer Doc Required')
    fields_ids = fields.Many2many('ir.model.fields', string='Required Fields')
    is_send_email = fields.Boolean('Is Send Email')


    @api.onchange('group_ids')
    def onchange_group_ids(self):
        for rec in self:
            users = []
            for group in rec.group_ids:
                users += group.users.ids
            rec.approval_user_ids = [(6, 0, users)]


class RemarksRefund(models.Model):
    _name = 'remarks.approval.ownership2'
    _description = 'Approval Remarks Ownership2'
    _order = 'remark_datettime desc'

    # ownership_id_2 = fields.Many2one('ownership.contract', string='Customer Onboarding')
    name = fields.Char('Remarks')
    user_id = fields.Many2one('res.users', string='User')
    remark_datettime = fields.Datetime(string='Remark Datetime')
    from_stage_id_2 = fields.Many2one('approval.level.ownership2', string='From Stage', required=False)
    to_stage_id_2 = fields.Many2one('approval.level.ownership2', string='To Stage')
    consumed_hours = fields.Char(string='Duration B/W the Stages')
    remark_type = fields.Selection([('approve', 'Approved'), ('previous', 'Previous'), ('reject', 'Reject')])