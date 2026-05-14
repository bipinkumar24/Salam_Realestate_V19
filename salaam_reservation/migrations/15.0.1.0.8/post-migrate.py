# -*- coding: utf-8 -*-
"""
Migration 15.0.1.0.8 — Remove stale pre_application_id field from ir.model.fields.

When the field was renamed from pre_application_id to bre_application_id,
the old ir.model.fields record was not cleaned up. Odoo's onchange mechanism
uses ir.model.fields to build the initial values dict, causing a KeyError.
"""
import logging
_logger = logging.getLogger(__name__)


def migrate(cr, version):
    # Remove the stale pre_application_id field record from ir.model.fields
    cr.execute("""
        DELETE FROM ir_model_fields
        WHERE model = 'salaam.reservation'
          AND name = 'pre_application_id';
    """)
    rows = cr.rowcount
    _logger.info(
        'salaam_reservation 15.0.1.0.8: removed %d stale pre_application_id '
        'field record(s) from ir_model_fields', rows
    )

    # Also remove any ir.model.access rows that reference the old field name
    cr.execute("""
        DELETE FROM ir_model_access
        WHERE name LIKE '%pre_customer_application%'
           OR name LIKE '%pre.customer.application%';
    """)

    # Drop pre_customer_application table if somehow still present
    cr.execute("DROP TABLE IF EXISTS pre_customer_application CASCADE;")

    # Drop stale FK on bre_application_id
    cr.execute("""
        ALTER TABLE salaam_reservation
        DROP CONSTRAINT IF EXISTS salaam_reservation_bre_application_id_fkey;
    """)
    cr.execute("""
        ALTER TABLE salaam_reservation
        DROP CONSTRAINT IF EXISTS salaam_reservation_pre_application_id_fkey;
    """)
