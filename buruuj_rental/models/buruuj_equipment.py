# -*- coding: utf-8 -*-
from odoo import models, fields


class BuruujEquipment(models.Model):
    _inherit = "buruuj.equipment"

    rental_contract_id = fields.Many2one(
        "buruuj.rental.contract", string="Rental Contract",
        help="If this equipment is rented in, the active rental contract.")
