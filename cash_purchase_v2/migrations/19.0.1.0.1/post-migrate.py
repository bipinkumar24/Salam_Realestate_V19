# -*- coding: utf-8 -*-
"""Drop purchase_mode column and patch any stored view arches."""
import logging, re
_logger = logging.getLogger(__name__)

def migrate(cr, version):
    cr.execute("ALTER TABLE bre_customer_application DROP COLUMN IF EXISTS purchase_mode;")
    cr.execute("DELETE FROM ir_model_fields WHERE model='bre.customer.application' AND name='purchase_mode';")

    cr.execute("SELECT id, arch_db FROM ir_ui_view WHERE model='bre.customer.application' AND arch_db LIKE '%purchase_mode%';")
    for vid, arch in cr.fetchall():
        if not arch: continue
        p = arch
        p = p.replace("'purchase_mode', '=', 'cash'",    "'financing_type', '=', 'cash'")
        p = p.replace("'purchase_mode','=','cash'",       "'financing_type','=','cash'")
        p = p.replace("'purchase_mode', '!=', 'cash'",   "'financing_type', '!=', 'cash'")
        p = p.replace("'purchase_mode', '=', 'financing'","'financing_type', '!=', 'cash'")
        p = p.replace("'purchase_mode','=','financing'",  "'financing_type','!=','cash'")
        p = re.sub(r'<field[^>]*name=["\']purchase_mode["\'][^/]*/>', '', p)
        if p != arch:
            cr.execute("UPDATE ir_ui_view SET arch_db=%s WHERE id=%s;", (p, vid))
            _logger.info('Patched view id=%d', vid)

    _logger.info('cash_purchase_v2: purchase_mode removed from DB')
