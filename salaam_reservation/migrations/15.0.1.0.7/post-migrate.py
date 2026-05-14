# -*- coding: utf-8 -*-
"""
Migration 15.0.1.0.7 — Remove pre.customer.application from the database.
The bre_application_id column already exists with the correct name - keep it.
"""
import logging
_logger = logging.getLogger(__name__)


def migrate(cr, version):
    # Drop pre_customer_application table if it exists
    cr.execute("DROP TABLE IF EXISTS pre_customer_application CASCADE;")

    # Remove ir.model.access entries for pre.customer.application
    cr.execute("""
        DELETE FROM ir_model_access
        WHERE name LIKE '%pre_customer_application%'
           OR name LIKE '%pre.customer.application%';
    """)

    # Remove ir.model.fields for this model
    cr.execute("""
        DELETE FROM ir_model_fields
        WHERE model = 'pre.customer.application';
    """)

    # Remove the ir.model record
    cr.execute("""
        DELETE FROM ir_model
        WHERE model = 'pre.customer.application';
    """)

    # Remove ir.ui.view records
    cr.execute("""
        DELETE FROM ir_ui_view
        WHERE model = 'pre.customer.application';
    """)

    # Remove ir.actions.act_window records
    cr.execute("""
        DELETE FROM ir_act_window
        WHERE res_model = 'pre.customer.application';
    """)

    # Remove the APP/YYYY sequence
    cr.execute("""
        DELETE FROM ir_sequence
        WHERE code = 'pre.customer.application';
    """)

    # Drop stale FK on bre_application_id only if it points to the wrong table
    cr.execute("""
        ALTER TABLE salaam_reservation
        DROP CONSTRAINT IF EXISTS salaam_reservation_bre_application_id_fkey;
    """)

    _logger.info('salaam_reservation 15.0.1.0.7: pre.customer.application purged from DB')
