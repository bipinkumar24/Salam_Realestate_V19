# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class BuruujTender(models.Model):
    """Tender / Opportunity record.

    Captures the full lifecycle from lead to award. On winning, the tender
    is converted into a Project with a frozen baseline budget."""
    _name = 'buruuj.tender'
    _description = 'Tender / Bid Opportunity'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'submission_deadline desc, id desc'

    name = fields.Char(string='Tender Reference', required=True, copy=False,
                       default=lambda self: _('New'), tracking=True)
    title = fields.Char(string='Tender Title', required=True, tracking=True)
    client_id = fields.Many2one(
        'res.partner', string='Client', required=True, tracking=True,
        domain=[('is_client', '=', True)])
    consultant_id = fields.Many2one(
        'res.partner', string='Consultant',
        domain=[('is_consultant', '=', True)])

    project_type = fields.Selection([
        ('building', 'Building'),
        ('infrastructure', 'Infrastructure'),
        ('road', 'Roads & Bridges'),
        ('mep', 'MEP'),
        ('fitout', 'Fit-out'),
        ('other', 'Other'),
    ], string='Project Type', default='building', tracking=True)

    location = fields.Char(string='Project Location')
    issue_date = fields.Date(string='RFQ Issue Date')
    submission_deadline = fields.Datetime(
        string='Submission Deadline', tracking=True,
        help='Final deadline for bid submission.')
    duration_months = fields.Integer(string='Estimated Duration (months)')

    estimated_value = fields.Monetary(string='Estimated Value', tracking=True)
    bid_value = fields.Monetary(string='Our Bid Value', tracking=True,
                                compute='_compute_bid_value', store=True)
    awarded_value = fields.Monetary(string='Awarded Value', tracking=True)
    currency_id = fields.Many2one(
        'res.currency', default=lambda self: self.env.company.currency_id)

    state = fields.Selection([
        ('draft', 'Draft'),
        ('estimating', 'Estimation'),
        ('reviewing', 'Internal Review'),
        ('submitted', 'Submitted'),
        ('won', 'Won'),
        ('lost', 'Lost'),
        ('cancelled', 'Cancelled'),
    ], default='draft', tracking=True, copy=False)

    boq_id = fields.Many2one('buruuj.boq', string='Bill of Quantities',
                             copy=False, ondelete='set null')
    estimator_id = fields.Many2one(
        'res.users', string='Lead Estimator',
        default=lambda self: self.env.user, tracking=True)
    overhead_percent = fields.Float(string='Overhead %', default=8.0)
    profit_percent = fields.Float(string='Profit %', default=10.0)
    contingency_percent = fields.Float(string='Contingency %', default=2.0)

    project_id = fields.Many2one('project.project', string='Awarded Project',
                                 readonly=True, copy=False)
    win_loss_reason = fields.Text(string='Win / Loss Reason')

    # Documents and notes
    notes = fields.Html(string='Internal Notes')
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)

    @api.depends('boq_id', 'boq_id.total_amount',
                 'overhead_percent', 'profit_percent', 'contingency_percent')
    def _compute_bid_value(self):
        for rec in self:
            base = rec.boq_id.total_amount if rec.boq_id else 0.0
            markup = (rec.overhead_percent + rec.profit_percent + rec.contingency_percent) / 100.0
            rec.bid_value = base * (1.0 + markup)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'buruuj.tender') or _('New')
        return super().create(vals_list)

    # ---- Workflow buttons ----
    def action_start_estimation(self):
        self.state = 'estimating'

    def action_send_for_review(self):
        for rec in self:
            if not rec.boq_id or not rec.boq_id.line_ids:
                raise UserError(_('Cannot send for review without a BOQ.'))
            rec.state = 'reviewing'

    def action_submit(self):
        self.state = 'submitted'

    def action_won(self):
        self.state = 'won'

    def action_lost(self):
        self.state = 'lost'

    def action_cancel(self):
        self.state = 'cancelled'

    def action_reset_draft(self):
        self.state = 'draft'

    def action_convert_to_project(self):
        """Create a project.project from a won tender, with the bid as baseline."""
        self.ensure_one()
        if self.state != 'won':
            raise UserError(_('Only won tenders can be converted to projects.'))
        if self.project_id:
            raise UserError(_('A project is already linked to this tender.'))
        Project = self.env['project.project']
        project_code = self.env['ir.sequence'].next_by_code('buruuj.project.code')
        project = Project.create({
            'name': self.title,
            'partner_id': self.client_id.id,
            'buruuj_tender_id': self.id,
            'buruuj_project_code': project_code,
            'buruuj_contract_value': self.awarded_value or self.bid_value,
            'buruuj_baseline_budget': self.bid_value,
        })
        self.project_id = project.id
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'project.project',
            'res_id': project.id,
            'view_mode': 'form',
        }

    def action_open_project(self):
        self.ensure_one()
        if not self.project_id:
            return False
        return {
            'type': 'ir.actions.act_window',
            'name': 'Project',
            'res_model': 'project.project',
            'res_id': self.project_id.id,
            'view_mode': 'form',
        }
