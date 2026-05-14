# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class BuruujToolTransfer(models.Model):
    """Tool transfer between sites with handover sign-off."""
    _name = 'buruuj.tool.transfer'
    _description = 'Tool Transfer'
    _inherit = ['mail.thread']
    _order = 'date desc, id desc'

    name = fields.Char(copy=False, default=lambda s: _('New'))
    tool_id = fields.Many2one('buruuj.tool', required=True, tracking=True)
    date = fields.Date(default=fields.Date.context_today, required=True,
                         tracking=True)
    from_project_id = fields.Many2one('project.project', string='From Site',
                                        required=True)
    to_project_id = fields.Many2one('project.project', string='To Site',
                                      required=True)
    from_storekeeper_id = fields.Many2one('hr.employee',
                                            string='Sent By (Storekeeper)')
    to_storekeeper_id = fields.Many2one('hr.employee',
                                          string='Received By (Storekeeper)')
    transport_method = fields.Selection([
        ('vehicle', 'Company Vehicle'),
        ('courier', 'Courier'),
        ('hand', 'Hand Carry'),
    ], default='vehicle')
    condition_at_dispatch = fields.Selection([
        ('new', 'New'),
        ('good', 'Good'),
        ('fair', 'Fair'),
        ('poor', 'Poor'),
    ], default='good')
    condition_at_receipt = fields.Selection([
        ('new', 'New'),
        ('good', 'Good'),
        ('fair', 'Fair'),
        ('poor', 'Poor'),
        ('damaged', 'Damaged in Transit'),
    ])
    notes = fields.Text()

    state = fields.Selection([
        ('draft', 'Draft'),
        ('dispatched', 'Dispatched'),
        ('received', 'Received'),
        ('cancelled', 'Cancelled'),
    ], default='draft', tracking=True)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'buruuj.tool.transfer') or _('New')
        return super().create(vals_list)

    @api.constrains('from_project_id', 'to_project_id')
    def _check_different_sites(self):
        for rec in self:
            if rec.from_project_id == rec.to_project_id:
                raise UserError(_(
                    'From and To sites must be different.'))

    def action_dispatch(self):
        for rec in self:
            rec.state = 'dispatched'

    def action_receive(self):
        for rec in self:
            if not rec.condition_at_receipt:
                raise UserError(_(
                    'Please rate the condition on receipt before confirming.'))
            rec.state = 'received'
            # Update tool location
            new_condition = (rec.condition_at_receipt if rec.condition_at_receipt
                             not in (False, None) else rec.tool_id.current_condition)
            rec.tool_id.write({
                'current_project_id': rec.to_project_id.id,
                'current_location': 'site_store',
                'current_condition': new_condition,
            })

    def action_cancel(self):
        self.state = 'cancelled'
