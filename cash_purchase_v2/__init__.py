# -*- coding: utf-8 -*-
from . import models
from . import controllers


def pre_init_hook(cr):
    
    from odoo import api, SUPERUSER_ID
    import logging
    _logger = logging.getLogger(__name__)

    # If cr is Environment, get cursor
    if hasattr(cr, 'cr'):
        cr = cr.cr
    """Drop purchase_mode column before model setup."""
    cr.execute("ALTER TABLE bre_customer_application DROP COLUMN IF EXISTS purchase_mode;")
    cr.execute("DELETE FROM ir_model_fields WHERE model='bre.customer.application' AND name='purchase_mode';")
    _logger.info('cash_purchase_v2 pre_init_hook: purchase_mode dropped')
