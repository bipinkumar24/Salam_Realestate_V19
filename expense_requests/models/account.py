from odoo import fields, models, api, _
from odoo.exceptions import UserError, ValidationError


class Emp(models.Model):
    _name = 'emp.fee'
    _description = 'Employee Fee'

    account_id = fields.Many2one('account.move', string='account')
    employees_id = fields.Many2one('res.partner', string='Name')
    description = fields.Text('Description')
    Amount = fields.Char(string=" Amount $")
    scheduled_date = fields.Date(string='Date')
    phone = fields.Char(string='Tell')


class Account(models.Model):
    _inherit = 'account.move'

    is_expense = fields.Boolean(string='Is Expense')
    department_id = fields.Many2one('hr.department', string='Department',
                                    default=lambda self: self._get_default_department())
    employees_fee_ids = fields.One2many('emp.fee', 'account_id', string=' ')
    amount_paid = fields.Float(string="amount_paid")

    def _get_default_department(self):
        user = self.env.user
        return user.department_id.id if user.department_id else False

    def _validate_required_approval_fields(self, vals=None):
        vals = vals or {}
        for rec in self:
            if not rec.next_approval_id:
                continue
            missing_fields = []
            for field in rec.next_approval_id.fields_ids:
                value = vals[field.name] if field.name in vals else rec[field.name]
                if value in (False, None, ''):
                    missing_fields.append(field.field_description)
            if missing_fields:
                raise ValidationError(
                    _("Required fields are: %s") % ", ".join(missing_fields)
                )

    @api.model
    def create(self, vals):
        rec = super().create(vals)
        rec._validate_required_approval_fields(vals)
        if rec.next_approval_id:
            rec.remark_ids = [(0, 0, {
                'name': "New Created",
                'user_id': self.env.user.id,
                'remark_datettime': fields.Datetime.now(),
                'to_stage_id': rec.next_approval_id.id,
                'remark_type': 'approve',
            })]
        return rec

    def write(self, vals):
        self._validate_required_approval_fields(vals)
        return super().write(vals)

    def _compute_is_customer_doc_required(self):
        for rec in self:
            rec.is_customer_doc_required = rec.next_approval_id.is_customer_doc_required

    def _write_company_type(self):
        for partner in self:
            partner.is_company = partner.company_type == 'company'

    @api.depends('next_approval_id', 'next_approval_id.approval_user_ids')
    def _compute_next_approval_user_id(self):
        for rec in self:
            rec.next_approval_user_ids = [(6, 0, rec.next_approval_id.approval_user_ids.ids)]

    @api.depends('next_approval_id', 'next_approval_user_ids')
    def _compute_is_button(self):
        for rec in self:
            if rec.env.user.id in rec.next_approval_user_ids.ids:
                rec.is_button = True
            else:
                rec.is_button = False

            if rec.next_approval_id.is_last_approval or rec.next_approval_id.is_reject:
                rec.is_button = False
            if rec.next_approval_id.is_last_approval:
                rec.is_last_level = True
            elif rec.state_2 == 'finance':
                rec.is_last_level = True
            else:
                rec.is_last_level = False

    @api.depends('next_approval_id')
    def _compute_is_first(self):
        for rec in self:
            if rec.next_approval_id.level == 1:
                rec.is_first = True
            else:
                rec.is_first = False

    not_finance = fields.Boolean(string='not finance', compute='_compute_not_finance')

    @api.depends('is_first', 'state_2', )
    def _compute_not_finance(self):
        for rec in self:
            if rec.is_first and not rec.require_hr:
                rec.not_finance = True
            elif rec.is_first and rec.require_hr and rec.state_2 != 'finance':
                rec.not_finance = True
            else:
                rec.not_finance = False

    def _get_next_approval_id(self):
        rec = self.env['approval.level.account'].search([('level', '=', 1)])
        return rec.id

    next_approval_id = fields.Many2one('approval.level.account', string='Next Approval', tracking=True,
                                       default=_get_next_approval_id)
    level = fields.Integer(related="next_approval_id.level")
    next_approval_user_ids = fields.Many2many('res.users', string='Next Approval By',
                                              compute='_compute_next_approval_user_id', store=True)
    is_button = fields.Boolean('Is button', compute='_compute_is_button')
    is_first = fields.Boolean('Is button', compute='_compute_is_first')
    is_last_level = fields.Boolean('Is button', compute='_compute_is_button')
    remark_ids = fields.One2many('remarks.approval.account', 'move_id', string='Remarks', tracking=True)
    is_customer_doc_required = fields.Boolean(string='Is Customer Doc Required',
                                              compute='_compute_is_customer_doc_required')
    require_hr = fields.Boolean(string='Requires HR Approval')
    require_gm = fields.Boolean(string='Requires GM Approval')
    require_custom_gm = fields.Boolean(string='Requires GM Approval')
    department_approved = fields.Boolean(string='Require HR')

    state_2 = fields.Selection(
        [
            ("new", "Draft"),
            ("depapproved", "Dep/site Manager Approved"),
            ("hr", "HR Approved"),
            ("togm", "Submitted to GM"),
            ("finance", "Submited for Payment"),
            ("reject", "Rejected"),

        ],
        string="Vehicle Status",
        default="new",
    )
    hide_hide_gm = fields.Boolean(string="Hide Gm", compute="_compute_hide_hide_gm")

    def _send_group_notification(self, group_xmlid, subject, body_prefix):
        partner_ids = self.env.ref(group_xmlid).users.mapped('partner_id').ids
        if not partner_ids:
            return
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        body_html = f"{body_prefix}<br/>{base_url}/web#id={self.id}&view_type=form&model={self._name}"
        values = {
            'subject': subject,
            'body_html': body_html,
            'email_from': self.env.user.email or None,
            'auto_delete': False,
            'recipient_ids': [(6, 0, partner_ids)],
        }
        self.env['mail.mail'].sudo().create(values).send()

    def gm_approve(self):
        for rec in self:
            rec.state_2 = 'finance'

    def _compute_hide_hide_gm(self):
        for account in self:
            if account.next_approval_id.level == 2:
                account.hide_hide_gm = False
            else:
                account.hide_hide_gm = True

    def cancel_it(self):
        for rec in self:
            rec.state_2 = 'reject'

    def submit_to_gm(self):
        for rec in self:
            rec.state_2 = 'togm'

    def department_approve(self):
        for rec in self:
            rec.department_approved = True
            rec.state_2 = 'depapproved'
            rec._send_group_notification(
                'expense_requests.department_approver',
                'Dept/Site Manager Approval',
                'Dept/Site Manager Approval',
            )

        return

    def hr_approve(self):
        for rec in self:
            rec.state_2 = 'hr'
            rec._send_group_notification(
                'expense_requests.hr_approver',
                'HR Approval',
                'HR Approval',
            )

        return

    def finance_approve(self):
        for rec in self:
            rec.state_2 = 'finance'
            rec._send_group_notification(
                'expense_requests.Finance_approver',
                'Finance Approval',
                'Finance Approval',
            )

        return

    def action_approve(self):
        view_id = self.env.ref('expense_requests.account_remark_wizard_view').id
        return {'type': 'ir.actions.act_window',
                'name': _('Remarks'),
                'res_model': 'account.remark.wizard',
                'target': 'new',
                'view_mode': 'form',
                'views': [[view_id, 'form']],
                }

    @api.depends('is_company')
    def _compute_company_type(self):
        for partner in self:
            partner.company_type = 'company' if partner.is_company else 'person'

    def submit_to_gm_dynamic(self):
        level_rec = self.env['approval.level.account'].search([('level', '=', 3)], limit=1)
        if level_rec:
            self.require_custom_gm = False
            self.next_approval_id = level_rec.id


    def gm_approve_custom(self):
        level_rec = self.env['approval.level.account'].search([('level', '=', 4)], limit=1)
        if level_rec:
            self.next_approval_id = level_rec.id

    def gm_approve_reject(self):
        level_rec = self.env['approval.level.account'].search([('is_reject', '=', True)], limit=1)
        if not level_rec:
            raise UserError(_("Please Configure Reject Level First or Contact to Administrator"))
        self.next_approval_id = level_rec.id
