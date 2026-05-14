# -*- coding: utf-8 -*-
from odoo import models, api

class IrUiViewPatch(models.Model):
    _inherit = 'ir.ui.view'

    @api.model
    def _patch_property_details_inherit(self, inherit_view_id, view_name):
        base_view = self.search([
            ('model', '=', 'property.details'),
            ('type', '=', 'form'),
            ('mode', '=', 'base'),
        ], limit=1)
        if not base_view:
            base_view = self.search([
                ('model', '=', 'property.details'),
                ('type', '=', 'form'),
            ], limit=1)
        if base_view and inherit_view_id:
            v = self.browse(inherit_view_id)
            if v.exists():
                v.write({'inherit_id': base_view.id})
