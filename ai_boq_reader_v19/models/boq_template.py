# -*- coding: utf-8 -*-
from odoo import models, fields, api


class BoqTemplate(models.Model):
    _name = 'ai.boq.template'
    _description = 'BOQ Template'
    _order = 'name'

    name = fields.Char(required=True)
    active = fields.Boolean(default=True)
    description = fields.Text()
    line_ids = fields.One2many('ai.boq.template.line', 'template_id', string='Template Lines', copy=True)
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)


class BoqTemplateLine(models.Model):
    _name = 'ai.boq.template.line'
    _description = 'BOQ Template Line'
    _order = 'sequence, id'

    template_id = fields.Many2one('ai.boq.template', required=True, ondelete='cascade')
    sequence = fields.Integer(default=10)
    category = fields.Selection([
        ('civil', 'Civil'),
        ('structural', 'Structural'),
        ('electrical', 'Electrical'),
        ('plumbing', 'Plumbing / MEP'),
        ('finishes', 'Finishes'),
        ('other', 'Other'),
    ], required=True, default='civil')
    description = fields.Char(required=True)
    product_id = fields.Many2one('product.product')
    uom_id = fields.Many2one('uom.uom')
    default_quantity = fields.Float(default=0.0)
    default_unit_price = fields.Float(default=0.0)
