# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class BuruujToolIssuance(models.Model):
    """Tool checked out to a worker. Returned with condition rating."""
    _name = 'buruuj.tool.issuance'
    _description = 'Tool Issuance'
    _inherit = ['mail.thread']
    _order = 'issue_date desc, id desc'

    name = fields.Char(copy=False, default=lambda s: _('New'))
    tool_id = fields.Many2one('buruuj.tool', required=True, tracking=True,
                                ondelete='restrict')
    employee_id = fields.Many2one('hr.employee', string='Issued To',
                                    required=True, tracking=True)
    project_id = fields.Many2one('project.project', string='Project / Site',
                                   tracking=True)
    issue_date = fields.Datetime(default=fields.Datetime.now, required=True,
                                   tracking=True)
    expected_return = fields.Date(string='Expected Return Date')
    actual_return = fields.Datetime(string='Returned On', readonly=True)
    condition_out = fields.Selection([
        ('new', 'New'),
        ('good', 'Good'),
        ('fair', 'Fair'),
        ('poor', 'Poor'),
    ], string='Condition Out', required=True, default='good')
    condition_in = fields.Selection([
        ('good', 'Returned Good'),
        ('fair', 'Returned Fair'),
        ('poor', 'Returned Poor'),
        ('damaged', 'Damaged'),
        ('not_returned', 'Not Returned'),
    ], string='Condition In', readonly=True)

    issued_by = fields.Many2one('res.users', string='Issued By',
                                  default=lambda s: s.env.user)
    received_by = fields.Many2one('res.users', string='Returned to',
                                    readonly=True)
    notes = fields.Text()

    state = fields.Selection([
        ('issued', 'Issued'),
        ('returned', 'Returned'),
        ('overdue', 'Overdue'),
        ('lost', 'Marked Lost'),
    ], default='issued', tracking=True)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'buruuj.tool.issuance') or _('New')
        records = super().create(vals_list)
        # Update tool state
        for rec in records:
            if rec.tool_id and rec.state == 'issued':
                rec.tool_id.write({
                    'current_location': 'issued',
                    'current_holder_id': rec.employee_id.id,
                    'current_project_id': rec.project_id.id,
                })
        return records

    def action_return(self):
        """Mark the tool as returned. Updates the tool state and condition."""
        for rec in self:
            if rec.state != 'issued':
                raise UserError(_('Only issued tools can be returned.'))
            if not rec.condition_in:
                raise UserError(_(
                    'Please rate the returned condition before saving.'))
            rec.write({
                'state': 'returned',
                'actual_return': fields.Datetime.now(),
                'received_by': self.env.user.id,
            })
            # Update tool master
            new_condition = (rec.condition_in if rec.condition_in != 'not_returned'
                             else rec.tool_id.current_condition)
            new_location = ('lost' if rec.condition_in == 'not_returned'
                            else 'main_store')
            rec.tool_id.write({
                'current_location': new_location,
                'current_holder_id': False,
                'current_condition': new_condition,
            })

    def action_mark_lost(self):
        """If a worker cannot return the tool, mark as lost."""
        for rec in self:
            rec.write({
                'state': 'lost',
                'condition_in': 'not_returned',
                'actual_return': fields.Datetime.now(),
            })
            rec.tool_id.write({
                'current_location': 'lost',
                'current_holder_id': False,
            })
            # Auto-create a loss record
            self.env['buruuj.tool.loss'].create({
                'tool_id': rec.tool_id.id,
                'incident_type': 'lost',
                'date': fields.Date.context_today(self),
                'responsible_employee_id': rec.employee_id.id,
                'project_id': rec.project_id.id,
                'description': f"Tool not returned from issuance {rec.name}",
                'estimated_value': rec.tool_id.purchase_value,
                'state': 'reported',
            })
