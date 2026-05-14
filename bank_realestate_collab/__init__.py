# -*- coding: utf-8 -*-
from . import models
from . import wizard
from . import controllers


def pre_init_hook(env):
    """
    Drop the purchase_mode column before model setup.
    financing_type already exists and is already populated — no data migration needed.
    """
    import logging
    _logger = logging.getLogger(__name__)

    # Odoo 19 passes an Environment to pre_init hooks; older versions pass a cursor.
    cr = env.cr if hasattr(env, 'cr') else env

    # Drop purchase_mode column if it exists
    cr.execute("""
        ALTER TABLE IF EXISTS bre_customer_application
        DROP COLUMN IF EXISTS purchase_mode;
    """)
    _logger.info('bank_realestate_collab: dropped purchase_mode column')

    # Remove its ir_model_fields record
    cr.execute("""
        DELETE FROM ir_model_fields
        WHERE model = 'bre.customer.application'
          AND name = 'purchase_mode';
    """)
    _logger.info('bank_realestate_collab: removed purchase_mode from ir_model_fields')
