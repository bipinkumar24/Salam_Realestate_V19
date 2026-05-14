# -*- coding: utf-8 -*-
from odoo import models, fields


class ResPartner(models.Model):
    _inherit = "res.partner"

    is_material_vendor = fields.Boolean(
        string="Is Material Vendor",
        help="Tick to flag this partner as a supplier of construction materials.")
    vendor_categories = fields.Char(
        string="Material Categories Supplied",
        help="Free-text list of material categories this vendor supplies, "
             "for quick search.")
