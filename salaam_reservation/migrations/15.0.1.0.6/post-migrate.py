import logging
_logger = logging.getLogger(__name__)

def migrate(cr, version):
    # Drop FK constraint if bre_application_id was previously a Many2one
    cr.execute("""
        ALTER TABLE salaam_reservation
        DROP CONSTRAINT IF EXISTS salaam_reservation_bre_application_id_fkey;
    """)
    # Also drop the column so Odoo recreates it as plain INTEGER
    cr.execute("""
        ALTER TABLE salaam_reservation
        DROP COLUMN IF EXISTS bre_application_id;
    """)
    _logger.info('salaam_reservation 15.0.1.0.6: reset bre_application_id to Integer')
