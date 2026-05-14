# -*- coding: utf-8 -*-
from . import models


def post_init_hook(env):
    """After installation, fix property.details view inheritance."""
    # from odoo import api, SUPERUSER_ID
    # env = api.Environment(cr, SUPERUSER_ID, {})

    base_view = env['ir.ui.view'].search([
        ('model', '=', 'property.details'),
        ('type', '=', 'form'),
        ('mode', '=', 'base'),
        ('name', 'not like', 'fallback'),
    ], order='priority asc', limit=1)

    if not base_view:
        base_view = env['ir.ui.view'].search([
            ('model', '=', 'property.details'),
            ('type', '=', 'form'),
            ('name', 'not like', 'fallback'),
        ], order='priority asc', limit=1)

    if base_view:
        our_view = env['ir.ui.view'].search([
            ('name', '=', 'property.details.construction.inherit'),
        ], limit=1)
        if our_view:
            our_view.write({'inherit_id': base_view.id})
