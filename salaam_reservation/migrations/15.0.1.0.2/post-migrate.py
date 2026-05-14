# -*- coding: utf-8 -*-
"""
Migration 15.0.1.0.2 — Ensure team_id column exists on salaam_reservation.
The column was added as a Many2one field but may not exist in DB yet.
"""
import logging
_logger = logging.getLogger(__name__)


def migrate(cr, version):
    # Drop team_id if it exists with wrong type, then let Odoo recreate it
    cr.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'salaam_reservation'
                AND column_name = 'team_id'
            ) THEN
                ALTER TABLE salaam_reservation
                ADD COLUMN team_id INTEGER;
                RAISE NOTICE 'Added team_id column to salaam_reservation';
            END IF;
        END $$;
    """)
    _logger.info('salaam_reservation: ensured team_id column exists')
