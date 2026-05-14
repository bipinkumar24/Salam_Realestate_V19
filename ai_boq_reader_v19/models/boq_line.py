# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


CATEGORY_SELECTION = [
    ('civil', 'Civil'),
    ('structural', 'Structural'),
    ('electrical', 'Electrical'),
    ('plumbing', 'Plumbing / MEP'),
    ('finishes', 'Finishes'),
    ('other', 'Other'),
]


class BoqLine(models.Model):
    _name = 'ai.boq.line'
    _description = 'BOQ Line Item'
    _order = 'boq_id, sequence, id'

    boq_id = fields.Many2one(
        'ai.boq.project', string='BOQ Project', required=True, ondelete='cascade', index=True)
    sequence = fields.Integer(default=10)
    category = fields.Selection(CATEGORY_SELECTION, required=True, default='civil', index=True)
    description = fields.Char(required=True)
    product_id = fields.Many2one('product.product', string='Product (optional)')
    uom_id = fields.Many2one('uom.uom', string='UoM')
    quantity = fields.Float(default=0.0, digits='Product Unit of Measure')
    unit_price = fields.Float(default=0.0, digits='Product Price')
    subtotal = fields.Monetary(compute='_compute_subtotal', store=True, currency_field='currency_id')
    currency_id = fields.Many2one(related='boq_id.currency_id', store=True, readonly=True)
    confidence_score = fields.Float(
        string='AI Confidence', help="0.0 - 1.0 confidence reported by the AI for this line.")
    confidence_band = fields.Selection(
        [('low', 'Low'), ('medium', 'Medium'), ('high', 'High')],
        compute='_compute_confidence_band', store=True)
    source_reference = fields.Char(string='Source Ref.', help="Drawing/zone reference, e.g. 'Sheet A-101, Grid B-C'")

    @api.depends('quantity', 'unit_price')
    def _compute_subtotal(self):
        for line in self:
            line.subtotal = (line.quantity or 0.0) * (line.unit_price or 0.0)

    @api.depends('confidence_score')
    def _compute_confidence_band(self):
        for line in self:
            c = line.confidence_score or 0.0
            line.confidence_band = 'high' if c >= 0.8 else ('medium' if c >= 0.5 else 'low')

    @api.onchange('product_id')
    def _onchange_product_id(self):
        if self.product_id:
            if not self.description:
                self.description = self.product_id.display_name
            self.uom_id = self.product_id.uom_id
            if not self.unit_price:
                self.unit_price = self.product_id.lst_price
