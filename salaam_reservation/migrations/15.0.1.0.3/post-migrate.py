# -*- coding: utf-8 -*-
"""Migration 15.0.1.0.3 — Fix stale FK constraints and security groups."""
import logging
_logger = logging.getLogger(__name__)

def migrate(cr, version):
    cr.execute("ALTER TABLE salaam_reservation DROP CONSTRAINT IF EXISTS salaam_reservation_crm_lead_id_fkey;")
    cr.execute("ALTER TABLE salaam_reservation DROP CONSTRAINT IF EXISTS salaam_reservation_bre_application_id_fkey;")
    _logger.info('salaam_reservation 15.0.1.0.3: FK constraints dropped')
