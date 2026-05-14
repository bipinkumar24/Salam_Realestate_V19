# -*- coding: utf-8 -*-
import logging
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class CashPaymentPlanTemplate(models.Model):
    _name        = 'cash.payment.plan.template'
    _description = 'Cash Purchase Payment Plan Template'
    _order       = 'plan_type, name'

    name      = fields.Char('Template Name', required=True)
    plan_type = fields.Selection([
        ('full',         'Full Payment Upfront'),
        ('instalment',   'Instalment Plan'),
        ('construction', 'Construction-Linked Plan'),
        ('custom',       'Custom Split'),
    ], string='Plan Type', required=True)

    description      = fields.Text('Description')
    active           = fields.Boolean(default=True)
    instalment_ids   = fields.One2many(
        'cash.payment.plan.template.line', 'template_id', 'Instalment Lines'
    )
    total_percentage = fields.Float(
        'Total %', compute='_compute_total', store=True
    )

    @api.depends('instalment_ids.percentage')
    def _compute_total(self):
        for r in self:
            r.total_percentage = sum(r.instalment_ids.mapped('percentage'))

    @api.constrains('instalment_ids')
    def _check_total(self):
        for r in self:
            if r.plan_type != 'custom' and r.instalment_ids:
                total = sum(r.instalment_ids.mapped('percentage'))
                if abs(total - 100.0) > 0.01:
                    raise ValidationError(
                        f'Instalment percentages must total 100%. Current total: {total:.2f}%'
                    )


class CashPaymentPlanTemplateLine(models.Model):
    _name        = 'cash.payment.plan.template.line'
    _description = 'Payment Plan Template Line'
    _order       = 'sequence'

    template_id  = fields.Many2one('cash.payment.plan.template', required=True, ondelete='cascade')
    sequence     = fields.Integer(default=10)
    name         = fields.Char('Milestone / Instalment Label', required=True)
    percentage   = fields.Float('Percentage (%)', required=True)
    trigger_type = fields.Selection([
        ('days',        'Days after booking'),
        ('months',      'Months after booking'),
        ('milestone',   'Construction milestone'),
        ('on_booking',  'On booking / signing'),
        ('on_handover', 'On handover'),
        ('custom_date', 'Specific date'),
    ], string='Due Date Basis', default='months')
    offset_value          = fields.Integer('Offset Value', default=0)
    milestone_description = fields.Char('Milestone Description')


class CashPaymentPlan(models.Model):
    _name        = 'cash.payment.plan'
    _description = 'Cash Purchase Payment Plan'
    _inherit     = ['mail.thread', 'mail.activity.mixin']
    _order       = 'create_date desc'

    name           = fields.Char('Reference', readonly=True, default='New')
    application_id = fields.Many2one(
        'bre.customer.application', 'Application', required=True,
        ondelete='cascade', tracking=True
    )
    partner_id  = fields.Many2one(related='application_id.partner_id', string='Client', store=True)
    property_id = fields.Many2one(related='application_id.property_id', string='Property', store=True)
    template_id = fields.Many2one('cash.payment.plan.template', 'Plan Template', tracking=True)
    plan_type   = fields.Selection([
        ('full',         'Full Payment Upfront'),
        ('instalment',   'Instalment Plan'),
        ('construction', 'Construction-Linked Plan'),
        ('custom',       'Custom Split'),
    ], string='Plan Type', required=True, tracking=True)

    total_amount  = fields.Monetary('Total Purchase Price', required=True,
                                    currency_field='currency_id', tracking=True)
    currency_id   = fields.Many2one('res.currency', default=lambda s: s.env.ref('base.USD'))
    booking_date  = fields.Date('Booking / Signing Date', default=fields.Date.today, required=True)
    state         = fields.Selection([
        ('draft',      'Draft'),
        ('confirmed',  'Confirmed'),
        ('in_progress','In Progress'),
        ('completed',  'Completed'),
        ('cancelled',  'Cancelled'),
    ], default='draft', tracking=True)

    line_ids          = fields.One2many('cash.payment.plan.line', 'plan_id', 'Payment Schedule')
    notes             = fields.Text('Notes / Special Conditions')
    total_scheduled   = fields.Monetary('Total Scheduled', compute='_compute_totals', store=True,
                                        currency_field='currency_id')
    total_paid        = fields.Monetary('Total Paid', compute='_compute_totals', store=True,
                                        currency_field='currency_id')
    total_outstanding = fields.Monetary('Outstanding', compute='_compute_totals', store=True,
                                        currency_field='currency_id')
    completion_pct    = fields.Float('Completion %', compute='_compute_totals', store=True)
    next_due_date     = fields.Date('Next Due Date', compute='_compute_next_due', store=True)
    next_due_amount   = fields.Monetary('Next Due Amount', compute='_compute_next_due', store=True,
                                        currency_field='currency_id')

    @api.depends('line_ids.amount', 'line_ids.paid', 'total_amount')
    def _compute_totals(self):
        for r in self:
            scheduled     = sum(r.line_ids.mapped('amount'))
            paid          = sum(r.line_ids.filtered('paid').mapped('amount'))
            r.total_scheduled   = scheduled
            r.total_paid        = paid
            r.total_outstanding = scheduled - paid
            r.completion_pct    = (paid / scheduled * 100) if scheduled else 0.0

    @api.depends('line_ids.due_date', 'line_ids.paid', 'line_ids.amount')
    def _compute_next_due(self):
        for r in self:
            unpaid = r.line_ids.filtered(lambda l: not l.paid).sorted('due_date')
            if unpaid:
                r.next_due_date   = unpaid[0].due_date
                r.next_due_amount = unpaid[0].amount
            else:
                r.next_due_date   = False
                r.next_due_amount = 0.0

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('cash.payment.plan') or 'New'
        return super().create(vals_list)

    def action_generate_schedule(self):
        self.ensure_one()
        if not self.total_amount:
            raise UserError(_('Set the Total Purchase Price before generating the schedule.'))
        self.line_ids.unlink()
        if self.template_id and self.template_id.instalment_ids:
            self._generate_from_template()
        elif self.plan_type == 'full':
            self._generate_full_upfront()
        elif self.plan_type == 'instalment':
            self._generate_default_instalment()
        elif self.plan_type == 'construction':
            self._generate_default_construction()
        else:
            self.env['cash.payment.plan.line'].create({
                'plan_id': self.id, 'sequence': 10,
                'name': 'Custom Payment 1', 'percentage': 100.0,
                'amount': self.total_amount, 'due_date': self.booking_date,
            })
        self.message_post(
            body=f'Payment schedule generated ({self.plan_type.replace("_"," ").title()} — {len(self.line_ids)} instalment(s)).',
            subtype_xmlid='mail.mt_note',
        )

    def _generate_from_template(self):
        bd = self.booking_date or date.today()
        for line in self.template_id.instalment_ids.sorted('sequence'):
            due = self._compute_due_date(line.trigger_type, line.offset_value, bd)
            self.env['cash.payment.plan.line'].create({
                'plan_id': self.id, 'sequence': line.sequence, 'name': line.name,
                'percentage': line.percentage,
                'amount': round(self.total_amount * line.percentage / 100, 2),
                'due_date': due, 'milestone': line.milestone_description or '',
            })

    def _generate_full_upfront(self):
        self.env['cash.payment.plan.line'].create({
            'plan_id': self.id, 'sequence': 10,
            'name': 'Full Payment — Due on Booking',
            'percentage': 100.0, 'amount': self.total_amount, 'due_date': self.booking_date,
        })

    def _generate_default_instalment(self):
        instalments = [
            (10, 'Booking Deposit',          30.0, 'on_booking', 0),
            (20, 'Progress Payment (50%)',   40.0, 'months',     6),
            (30, 'Final Payment / Handover', 30.0, 'on_handover',18),
        ]
        bd = self.booking_date or date.today()
        for seq, label, pct, trigger, offset in instalments:
            due = self._compute_due_date(trigger, offset, bd)
            self.env['cash.payment.plan.line'].create({
                'plan_id': self.id, 'sequence': seq, 'name': label,
                'percentage': pct,
                'amount': round(self.total_amount * pct / 100, 2), 'due_date': due,
            })

    def _generate_default_construction(self):
        milestones = [
            (10, 'Booking / Contract Signing',     10.0, 'on_booking', 0,  'Contract execution'),
            (20, 'Foundation Completion',           20.0, 'months',     4,  'Foundation slab complete'),
            (30, 'Structure Completion (50%)',      30.0, 'months',     10, 'Floors to mid-level complete'),
            (40, 'Structure Completion (100%)',     25.0, 'months',     16, 'Full structure complete'),
            (50, 'Handover / Snag Resolution',      15.0, 'on_handover',24, 'Unit handed over to buyer'),
        ]
        bd = self.booking_date or date.today()
        for seq, label, pct, trigger, offset, ms in milestones:
            due = self._compute_due_date(trigger, offset, bd)
            self.env['cash.payment.plan.line'].create({
                'plan_id': self.id, 'sequence': seq, 'name': label,
                'percentage': pct,
                'amount': round(self.total_amount * pct / 100, 2),
                'due_date': due, 'milestone': ms,
            })

    @staticmethod
    def _compute_due_date(trigger_type, offset_value, booking_date):
        bd = booking_date if isinstance(booking_date, date) else date.today()
        if trigger_type == 'on_booking':   return bd
        if trigger_type == 'on_handover':  return bd + relativedelta(months=offset_value or 24)
        if trigger_type == 'months':       return bd + relativedelta(months=offset_value)
        if trigger_type == 'days':         return bd + timedelta(days=offset_value)
        if trigger_type == 'milestone':    return bd + relativedelta(months=offset_value)
        return bd

    def action_confirm(self):
        self.ensure_one()
        if not self.line_ids:
            raise UserError(_('Generate a payment schedule before confirming.'))
        total_pct = sum(self.line_ids.mapped('percentage'))
        if abs(total_pct - 100.0) > 0.01:
            raise UserError(_(f'Payment lines must total 100%. Current: {total_pct:.2f}%'))
        self.write({'state': 'confirmed'})
        self.application_id.message_post(
            body=f'✅ Cash payment plan <b>{self.name}</b> confirmed — '
                 f'{len(self.line_ids)} instalment(s), total {self.currency_id.symbol}{self.total_amount:,.2f}',
            subtype_xmlid='mail.mt_note',
        )

    def action_cancel(self):     self.write({'state': 'cancelled'})
    def action_reset_draft(self): self.write({'state': 'draft'})


class CashPaymentPlanLine(models.Model):
    _name        = 'cash.payment.plan.line'
    _description = 'Cash Payment Plan Instalment'
    _order       = 'sequence, due_date'

    plan_id     = fields.Many2one('cash.payment.plan', required=True, ondelete='cascade')
    sequence    = fields.Integer(default=10)
    name        = fields.Char('Description', required=True)
    percentage  = fields.Float('Percentage (%)')
    amount      = fields.Monetary('Amount', currency_field='currency_id')
    currency_id = fields.Many2one(related='plan_id.currency_id')
    due_date    = fields.Date('Due Date', required=True)
    milestone   = fields.Char('Construction Milestone')
    paid        = fields.Boolean('Paid', default=False, tracking=True)
    paid_date   = fields.Date('Payment Date')
    paid_amount = fields.Monetary('Amount Received', currency_field='currency_id')
    receipt_ref = fields.Char('Receipt / Reference')
    notes       = fields.Char('Notes')
    status      = fields.Selection([
        ('pending', 'Pending'),
        ('due',     'Due'),
        ('overdue', 'Overdue'),
        ('paid',    'Paid'),
    ], compute='_compute_status', store=True)

    @api.depends('paid', 'due_date')
    def _compute_status(self):
        today = date.today()
        for r in self:
            if r.paid:
                r.status = 'paid'
            elif r.due_date and r.due_date < today:
                r.status = 'overdue'
            elif r.due_date and r.due_date <= today + timedelta(days=14):
                r.status = 'due'
            else:
                r.status = 'pending'

    def action_mark_paid(self):
        self.ensure_one()
        self.write({'paid': True, 'paid_date': fields.Date.today(), 'status': 'paid'})
        plan = self.plan_id
        if all(plan.line_ids.mapped('paid')):
            plan.write({'state': 'completed'})
            plan.application_id.message_post(
                body=f'🎉 Cash payment plan <b>{plan.name}</b> — all instalments received. Plan completed.',
                subtype_xmlid='mail.mt_note',
            )


# ─────────────────────────────────────────────────────────────────
# BRE Application — extend with cash purchase fields
# ALL conditions now use financing_type == 'cash' instead of purchase_mode
# ─────────────────────────────────────────────────────────────────

class BREApplicationCashExtension(models.Model):
    _inherit = 'bre.customer.application'

    # Cash-specific fields — purchase_mode REMOVED, use financing_type directly
    cash_plan_type = fields.Selection([
        ('full',         'Full Payment Upfront'),
        ('instalment',   'Instalment Plan'),
        ('construction', 'Construction-Linked Plan'),
        ('custom',       'Custom Split'),
    ], string='Cash Plan Type', tracking=True)

    cash_payment_plan_id = fields.Many2one(
        'cash.payment.plan', 'Payment Plan',
        compute='_compute_cash_plan', store=True,
    )
    cash_plan_count = fields.Integer('Payment Plans', compute='_compute_cash_plan_count')
    cash_plan_state = fields.Selection(
        related='cash_payment_plan_id.state', string='Plan Status', store=True,
    )
    skip_appraisal = fields.Boolean(
        'Skip Five Cs Appraisal', default=False,
        help='Automatically set for cash purchases.',
    )

    @api.depends('financing_type')
    def _compute_cash_plan(self):
        for r in self:
            plan = self.env['cash.payment.plan'].search(
                [('application_id', '=', r.id)], limit=1, order='create_date desc'
            )
            r.cash_payment_plan_id = plan

    def _compute_cash_plan_count(self):
        for r in self:
            r.cash_plan_count = self.env['cash.payment.plan'].search_count(
                [('application_id', '=', r.id)]
            )

    @api.onchange('financing_type')
    def _onchange_financing_type_cash(self):
        """React when financing_type switches to/from cash."""
        if self.financing_type == 'cash':
            self.financing_amount = 0
            self.down_payment     = 0
            self.tenure_months    = 0
            self.skip_appraisal   = True
            self.cash_plan_type   = 'instalment'
            return {
                'warning': {
                    'title':   'Cash Purchase Selected',
                    'message': (
                        'Financing Type is set to Cash Purchase.\n'
                        'Financing fields have been cleared.\n'
                        'A payment plan will be generated automatically.\n'
                        'The Five Cs appraisal will be skipped.'
                    ),
                }
            }
        else:
            self.skip_appraisal = False
            self.cash_plan_type = False

    @api.onchange('cash_plan_type')
    def _onchange_cash_plan_type(self):
        if self.financing_type == 'cash' and self.cash_plan_type:
            labels = {
                'full':         'Full Payment Upfront — 100% due on booking.',
                'instalment':   'Instalment Plan — 30% booking + 40% at 6 months + 30% on handover.',
                'construction': 'Construction-Linked — 5 milestone payments over the build period.',
                'custom':       'Custom Split — officer defines each instalment manually.',
            }
            return {
                'warning': {
                    'title':   'Payment Plan Type',
                    'message': labels.get(self.cash_plan_type, ''),
                }
            }

    def action_create_cash_plan(self):
        """Create a cash payment plan and open it."""
        self.ensure_one()
        if self.financing_type != 'cash':
            raise UserError(_('Set Financing Type to Cash Purchase first.'))
        if not self.cash_plan_type:
            raise UserError(_(
                'Please select a Cash Plan Type (e.g. Instalment Plan) '
                'before creating a payment plan.'
            ))
        property_price = (
            self.property_id.price
            if self.property_id and self.property_id.price
            else 0.0
        )
        total_amount = property_price or (self.financing_amount or 0.0)
        if not total_amount:
            raise UserError(_(
                'Cannot create a payment plan: the property has no listed price '
                'and no financing amount is set.\n\n'
                'Please set the property price or enter a financing amount first.'
            ))
        plan = self.env['cash.payment.plan'].create({
            'application_id': self.id,
            'plan_type':      self.cash_plan_type,
            'total_amount':   total_amount,
            'booking_date':   fields.Date.today(),
        })
        plan.action_generate_schedule()
        self._notify_agent_cash_purchase(plan)
        return {
            'type':      'ir.actions.act_window',
            'name':      'Cash Payment Plan',
            'res_model': 'cash.payment.plan',
            'res_id':    plan.id,
            'view_mode': 'form',
            'target':    'current',
        }

    def action_view_cash_plans(self):
        return {
            'type':      'ir.actions.act_window',
            'name':      'Payment Plans',
            'res_model': 'cash.payment.plan',
            'domain':    [('application_id', '=', self.id)],
            'view_mode': 'list,form',
            'target':    'current',
        }

    def _notify_agent_cash_purchase(self, plan):
        agent = self.agent_id if hasattr(self, 'agent_id') and self.agent_id else False
        tag   = f'@{agent.name}' if agent else 'Real Estate Agent'
        body  = (
            f'<b>💵 Cash Purchase — Payment Plan Created</b><br/>'
            f'<b>Client:</b> {self.partner_id.name}<br/>'
            f'<b>Property:</b> {self.property_id.name if self.property_id else "—"}<br/>'
            f'<b>Plan Type:</b> {(self.cash_plan_type or "").replace("_", " ").title()}<br/>'
            f'<b>Plan Reference:</b> {plan.name}<br/>'
            f'<b>Total Amount:</b> USD {plan.total_amount:,.2f}<br/>'
            f'<b>Instalments:</b> {len(plan.line_ids)}<br/>'
            f'<b>Action Required:</b> {tag} — please confirm the payment plan with the client.'
        )
        self.message_post(
            body=body,
            subtype_xmlid='mail.mt_note',
            partner_ids=[agent.partner_id.id] if agent and hasattr(agent, 'partner_id') else [],
        )

    def action_create_appraisal(self):
        self.ensure_one()
        if self.financing_type == 'cash':
            raise UserError(_(
                'This is a Cash Purchase application.\n'
                'Five Cs appraisal is not required.\n'
                'Use "Create Payment Plan" instead.'
            ))
        return super().action_create_appraisal()
