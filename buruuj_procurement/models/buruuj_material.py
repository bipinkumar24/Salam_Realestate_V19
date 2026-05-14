# -*- coding: utf-8 -*-
from odoo import models, fields, api


class BuruujMaterial(models.Model):
    """Master register of materials used across projects."""
    _name = "buruuj.material"
    _description = "Construction Material"
    _inherit = ["mail.thread"]
    _order = "code"

    name = fields.Char(string="Material Name", required=True, tracking=True)
    code = fields.Char(string="Material Code", required=True, copy=False,
                         tracking=True)
    category_id = fields.Many2one("buruuj.material.category",
                                    string="Category", required=True)
    uom_id = fields.Many2one("uom.uom", string="UoM", required=True)
    specification = fields.Text(
        help="Standard specification (grade, size, finish). Used as default in MRs.")
    last_purchase_price = fields.Monetary(readonly=True,
                                            help="Last known purchase price.")
    minimum_stock = fields.Float(string="Minimum Stock Level",
                                   help="Reorder threshold for the main store.")
    preferred_vendor_ids = fields.Many2many(
        "res.partner", string="Preferred Vendors",
        domain=[("supplier_rank", ">", 0)])
    notes = fields.Text()
    active = fields.Boolean(default=True)
    currency_id = fields.Many2one(
        "res.currency", default=lambda s: s.env.company.currency_id)
    company_id = fields.Many2one("res.company",
                                   default=lambda s: s.env.company)

    _sql_constraints = [
        ("code_unique", "unique(code, company_id)",
         "Material code must be unique."),
    ]

    @api.depends("name", "code")
    def _compute_display_name(self):
        for rec in self:
            rec.display_name = f"[{rec.code}] {rec.name}" if rec.code else rec.name
