# -*- coding: utf-8 -*-
from odoo import models, fields, api, _

# ══════════════════════════════════════════════════════════════════════════════
#  EXTENSION: property.details  →  add BRE-specific fields
#
#  Instead of maintaining our own property model we extend the existing
#  property.details model from rental_management.  All property name, type,
#  pricing, area, address, project, landlord and stage fields come from
#  the source model — we only add what is BRE-specific.
# ══════════════════════════════════════════════════════════════════════════════

class PropertyDetailsBREExtension(models.Model):
    _inherit = 'property.details'

    # ── BRE-specific fields ────────────────────────────────────────────────
    # Sharia compliance — not in rental_management
    is_sharia_compliant = fields.Boolean(
        string='Sharia Compliant', default=True, tracking=True)
    sharia_certificate_no = fields.Char(string='Sharia Certificate No.')
    sharia_certification_date = fields.Date(string='Sharia Certification Date')

    # BRE application back-reference
    bre_application_ids = fields.One2many(
        'bre.customer.application', 'property_id',
        string='BRE Applications')
    bre_application_count = fields.Integer(
        string='BRE Applications',
        compute='_compute_bre_application_count')

    @api.depends('bre_application_ids')
    def _compute_bre_application_count(self):
        for rec in self:
            rec.bre_application_count = len(rec.bre_application_ids)

    def action_view_bre_applications(self):
        return {
            'type': 'ir.actions.act_window',
            'name': _('BRE Applications'),
            'res_model': 'bre.customer.application',
            'view_mode': 'list,form',
            'domain': [('property_id', '=', self.id)],
            'context': {'default_property_id': self.id},
        }
