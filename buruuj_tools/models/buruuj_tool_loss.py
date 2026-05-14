# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class BuruujToolLoss(models.Model):
    """Lost, stolen, or damaged tool record. Supports cost recovery."""
    _name = 'buruuj.tool.loss'
    _description = 'Tool Loss / Damage'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date desc, id desc'

    name = fields.Char(compute='_compute_name', store=True)
    tool_id = fields.Many2one('buruuj.tool', required=True, tracking=True)
    incident_type = fields.Selection([
        ('lost', 'Lost'),
        ('stolen', 'Stolen'),
        ('damaged_repairable', 'Damaged - Repairable'),
        ('damaged_writeoff', 'Damaged - Write-off'),
    ], required=True, default='lost', tracking=True)
    date = fields.Date(default=fields.Date.context_today, required=True,
                         tracking=True)
    project_id = fields.Many2one('project.project', string='Project / Site')
    location = fields.Char(string='Location Last Seen')
    responsible_employee_id = fields.Many2one('hr.employee',
                                                string='Responsible Worker')
    responsible_subcontractor_id = fields.Many2one(
        'res.partner', string='Responsible Subcontractor',
        domain=[('is_subcontractor', '=', True)])
    description = fields.Text(required=True)

    estimated_value = fields.Monetary(string='Estimated Value')
    recovery_amount = fields.Monetary(
        string='Recovery Amount',
        help='Amount recovered from worker (payroll deduction) or subcontractor (back-charge).')
    recovery_method = fields.Selection([
        ('payroll', 'Payroll Deduction'),
        ('backcharge', 'Subcontractor Back-charge'),
        ('insurance', 'Insurance Claim'),
        ('writeoff', 'Written Off'),
        ('none', 'No Recovery'),
    ], string='Recovery Method')
    backcharge_id = fields.Many2one('buruuj.backcharge',
                                      string='Linked Back-charge', readonly=True)
    incident_report_attachment = fields.Binary(string='Incident Report (PDF)')
    incident_report_filename = fields.Char()

    state = fields.Selection([
        ('reported', 'Reported'),
        ('investigating', 'Under Investigation'),
        ('recovered', 'Cost Recovered'),
        ('written_off', 'Written Off'),
        ('disputed', 'Disputed'),
    ], default='reported', tracking=True)

    currency_id = fields.Many2one(
        'res.currency', default=lambda s: s.env.company.currency_id)

    @api.depends('tool_id', 'incident_type', 'date')
    def _compute_name(self):
        for rec in self:
            t = rec.tool_id.name or 'Tool'
            it = dict(rec._fields['incident_type'].selection).get(
                rec.incident_type, '')
            rec.name = f"{t} - {it} ({rec.date or ''})"

    def action_investigate(self):
        for rec in self:
            rec.state = 'investigating'

    def action_create_backcharge(self):
        """If responsible party is a subcontractor, create a back-charge."""
        self.ensure_one()
        if not self.responsible_subcontractor_id:
            from odoo.exceptions import UserError
            raise UserError(_(
                'A responsible subcontractor must be set to raise a back-charge.'))
        # Find an active subcontract with this partner
        Sub = self.env['buruuj.subcontract']
        subcontract = Sub.search([
            ('partner_id', '=', self.responsible_subcontractor_id.id),
            ('project_id', '=', self.project_id.id),
            ('state', 'in', ['signed', 'in_progress']),
        ], limit=1)
        if not subcontract:
            raise UserError(_(
                'No active subcontract found for this subcontractor on this project.'))
        backcharge = self.env['buruuj.backcharge'].create({
            'name': f"Tool loss: {self.tool_id.name}",
            'subcontract_id': subcontract.id,
            'date': self.date,
            'category': 'material',
            'description': self.description,
            'amount': self.recovery_amount or self.estimated_value,
            'state': 'draft',
        })
        self.backcharge_id = backcharge.id
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'buruuj.backcharge',
            'res_id': backcharge.id,
            'view_mode': 'form',
        }

    def action_recover(self):
        for rec in self:
            rec.state = 'recovered'
            # Mark tool as written off if loss was permanent
            if rec.incident_type in ('lost', 'stolen', 'damaged_writeoff'):
                rec.tool_id.write({
                    'active': False,
                    'current_location': 'lost' if rec.incident_type != 'damaged_writeoff'
                                         else 'written_off',
                })

    def action_writeoff(self):
        for rec in self:
            rec.state = 'written_off'
            rec.tool_id.write({
                'active': False,
                'current_location': 'written_off',
            })

    def action_dispute(self):
        for rec in self:
            rec.state = 'disputed'
