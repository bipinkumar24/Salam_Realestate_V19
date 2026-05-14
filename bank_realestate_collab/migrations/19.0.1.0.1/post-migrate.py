# -*- coding: utf-8 -*-
"""
Migration 19.0.1.0.1 — Remove purchase_mode from bre.customer.application.

purchase_mode (Selection: financing/cash) is replaced by the existing
financing_type field which was already present and populated.

Condition mapping:
  purchase_mode == 'cash'      → financing_type == 'cash'
  purchase_mode == 'financing' → financing_type != 'cash'
"""
import logging, re
_logger = logging.getLogger(__name__)


def migrate(cr, version):
    # Drop column (pre_init_hook already does this, but safe to repeat)
    cr.execute("""
        ALTER TABLE bre_customer_application
        DROP COLUMN IF EXISTS purchase_mode;
    """)
    cr.execute("""
        DELETE FROM ir_model_fields
        WHERE model = 'bre.customer.application'
          AND name = 'purchase_mode';
    """)

    # Patch all stored view arches that reference purchase_mode
    cr.execute("""
        SELECT id, arch_db FROM ir_ui_view
        WHERE model = 'bre.customer.application'
          AND arch_db LIKE '%purchase_mode%';
    """)
    rows = cr.fetchall()
    _logger.info('Patching %d view(s) that reference purchase_mode', len(rows))

    for view_id, arch_db in rows:
        if not arch_db:
            continue
        p = arch_db
        p = p.replace("'purchase_mode', '=', 'cash'",    "'financing_type', '=', 'cash'")
        p = p.replace("'purchase_mode','=','cash'",       "'financing_type','=','cash'")
        p = p.replace("'purchase_mode', '!=', 'cash'",   "'financing_type', '!=', 'cash'")
        p = p.replace("'purchase_mode','!=','cash'",      "'financing_type','!=','cash'")
        p = p.replace("'purchase_mode', '=', 'financing'","'financing_type', '!=', 'cash'")
        p = p.replace("'purchase_mode','=','financing'",  "'financing_type','!=','cash'")
        p = p.replace("'purchase_mode', '!=', 'financing'","'financing_type', '=', 'cash'")
        p = p.replace("'purchase_mode','!=','financing'", "'financing_type','=','cash'")
        # Remove standalone purchase_mode field tags
        p = re.sub(r'<field[^>]*name=["\']purchase_mode["\'][^/]*/>', '', p)
        p = re.sub(r'<field[^>]*name=["\']purchase_mode["\'][^>]*>.*?</field>', '', p, flags=re.DOTALL)
        if p != arch_db:
            cr.execute("UPDATE ir_ui_view SET arch_db = %s WHERE id = %s;", (p, view_id))
            _logger.info('  Patched view id=%d', view_id)

    # Patch ir_rule and ir_filters domains
    cr.execute("""
        UPDATE ir_rule
        SET domain_force = REPLACE(domain_force, 'purchase_mode', 'financing_type')
        WHERE domain_force LIKE '%purchase_mode%';
    """)
    cr.execute("""
        UPDATE ir_filters
        SET domain = REPLACE(domain, 'purchase_mode', 'financing_type')
        WHERE domain LIKE '%purchase_mode%';
    """)

    # Remove any constraints on the old field
    cr.execute("DELETE FROM ir_model_constraint WHERE name LIKE '%purchase_mode%';")

    _logger.info('bank_realestate_collab 19.0.1.0.1: purchase_mode fully removed')
