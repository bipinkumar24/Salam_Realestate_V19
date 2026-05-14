# -*- coding: utf-8 -*-
"""
Migration 15.0.1.0.1 — Drop stale FK constraints on Integer fields.

crm_lead_id and bre_application_id were previously Many2one fields.
Changing them to Integer does NOT automatically drop the PostgreSQL FK constraint.
This migration drops them so CRM leads and BRE records can be deleted freely.
"""
import logging
_logger = logging.getLogger(__name__)


def migrate(cr, version):
    constraints = [
        'salaam_reservation_crm_lead_id_fkey',
        'salaam_reservation_bre_application_id_fkey',
    ]
    for constraint in constraints:
        cr.execute("""
            ALTER TABLE salaam_reservation
            DROP CONSTRAINT IF EXISTS %s
        """ % constraint)
        _logger.info('salaam_reservation: dropped constraint %s (if existed)', constraint)
