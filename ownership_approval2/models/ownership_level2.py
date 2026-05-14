from odoo import fields, models, api, _
from odoo.exceptions import ValidationError

class Ownership2(models.Model):
    _inherit = 'ownership.contract'

    bbank = fields.Selection(
        [('sab', 'Salam African Bank'), ('other', 'Other')],
        string='Beneficiary Bank')

    @api.model
    def create(self, vals):
        rec = super(Ownership2, self).create(vals)
        required_fields = ''
        for field in rec.next_approval_id_2.fields_ids:
            required_fields += field.field_description + ", "
        for field in rec.next_approval_id_2.fields_ids:
            if self.env['ownership.contract'].search([(field.name, '=', False), ('id', '=', rec.id)]):
                raise ValidationError("Required Fields are %r" % required_fields)
        rec.remark2_ids = [(0, 0, {'name': "New Created",
                                   'user_id': self.env.user.id,
                                   'remark_datettime': fields.Datetime.now(),
                                   'from_stage_id_2': rec.next_approval_id_2.id,
                                   'remark_type': 'approve'
                                   })]
        return rec

    def write(self, vals):
        for rec in self:
            required_fields = ' '
            for field in rec.next_approval_id_2.fields_ids:
                required_fields += field.field_description + ","
            for field in rec.next_approval_id_2.fields_ids:
                if not vals.get(field.name):
                    if self.env['ownership.contract'].search([(field.name, '=', False), ('id', '=', rec.id)]):
                        raise ValidationError("Required Fields are %r" % required_fields)
        res = super(Ownership2, self).write(vals)
        return res

    # def _compute_is_doc_required(self):
    #     for rec in self:
    #         rec.is_prior_doc_required2 = rec.next_approval_id_2.is_prior_doc_required
    #         rec.is_res_doc_required2 = rec.next_approval_id_2.is_res_doc_required
    #         rec.is_sell_doc_required2 = rec.next_approval_id_2.is_sell_doc_required
    #         rec.is_final_doc_required2 = rec.next_approval_id_2.is_final_doc_required

    def _write_company_type(self):
        for partner in self:
            partner.is_company = partner.company_type == 'company'

    @api.depends('next_approval_id_2', 'next_approval_id_2.approval_user_ids')
    def _compute_next_approval_user_id(self):
        for rec in self:
            rec.next_approval_user_ids = [(6, 0, rec.next_approval_id_2.approval_user_ids.ids)]

    @api.depends('next_approval_id_2', 'next_approval_user_ids')
    def _compute_is_button(self):
        for rec in self:
            if self.env.user.id in rec.next_approval_user_ids.ids:
                rec.is_button = True
            else:
                rec.is_button = False

            if rec.next_approval_id_2.is_last_approval or rec.next_approval_id_2.is_reject:
                rec.is_button = False
            if rec.next_approval_id_2.is_last_approval:
                rec.is_last_level = True
            else:
                rec.is_last_level = False

    @api.onchange('fmode')
    def _compute_is_bank(self):
        for rec in self:
            if rec.fmode == 'bank':
                rec.is_bank = True
            else:
                rec.is_bank = False

    def _get_next_approval_id_2(self):
        rec = self.env['approval.level.ownership2'].search([('level', '=', 1)])
        return rec.id

    next_approval_id_2 = fields.Many2one('approval.level.ownership2', string='Approval Stage', tracking=True,
                                          default=lambda self: self._get_next_approval_id_2())
    next_approval_user_ids = fields.Many2many('res.users', string='Next Approval By',
                                              compute='_compute_next_approval_user_id', store=True)
    is_button = fields.Boolean('Is button', compute='_compute_is_button')
    is_bank = fields.Boolean('Is button', compute='_compute_is_bank')
    is_last_level = fields.Boolean('Is button', compute='_compute_is_button')
    remark2_ids = fields.One2many('remarks.approval.ownership2', 'ownership_id_2', string='Remarks', tracking=True)

    def action_approve2(self):
        view_id = self.env.ref('ownership_approval2.ownership_remark_wizard_wizard_view2').id
        return {'type': 'ir.actions.act_window',
                'name': _('Remarks'),
                'res_model': 'ownership.remark.wizard2',
                'target': 'new',
                'view_mode': 'form',
                'views': [[view_id, 'form']],
                }
