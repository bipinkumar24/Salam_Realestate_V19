# -*- coding: utf-8 -*-
from odoo.exceptions import UserError

from odoo import fields, models,api


class PropertySector(models.Model):
    _name = 'property.sector'
    _description = 'Business Sector / Industry Classification'
    _order = 'name'

    name = fields.Char(string='Sector Name', required=True)
    code = fields.Char(string='Code')
    active = fields.Boolean(default=True)

    _name_unique = models.Constraint(
        ('unique(name)', 'Sector name must be unique!.'),
    )

    @api.depends('name')
    def name_uniq(self):
        for record in self:
            if record.name:
                existing = self.search([('name', '=', record.name), ('id', '!=', record.id)], limit=1)
                if existing:
                    raise UserError('Sector name must be unique!')
