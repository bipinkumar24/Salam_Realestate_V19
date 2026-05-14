# -*- coding: utf-8 -*-
from . import models


# ─────────────────────────────────────────────────────────────────────────────
#  Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _table_exists(cr, table_name):
    """Return True if the given PostgreSQL table exists in the current DB."""
    cr.execute("""
        SELECT EXISTS (
            SELECT FROM information_schema.tables
            WHERE table_name = %s
        )
    """, (table_name,))
    return cr.fetchone()[0]


def _inject_salaam_crm_fields(env):
    """
    Directly inject Salaam Priority/File/Reservation fields into the real
    CRM lead form view by patching the inherit view's parent to be the
    actual CRM form, then force-writing a compatible arch.
    Called from post_init_hook.
    """
    from lxml import etree

    # Find the real CRM lead form view (lowest priority = main view)
    crm_views = env['ir.ui.view'].search([
        ('model', '=', 'crm.lead'),
        ('type', '=', 'form'),
        ('mode', '=', 'base'),
    ], order='priority asc')

    # Pick the one that is NOT our fallback
    crm_form_view = None
    for v in crm_views:
        if 'fallback' not in (v.name or ''):
            crm_form_view = v
            break

    if not crm_form_view:
        return  # CRM not installed or no form view found

    # Find our inherit view
    our_view = env['ir.ui.view'].search([
        ('name', '=', 'crm.lead.salaam.reservation.inherit'),
    ], limit=1)

    if not our_view:
        return

    # Get the real arch of the CRM form to discover what elements exist
    try:
        arch_str = crm_form_view.arch_db or crm_form_view.arch
        root = etree.fromstring(arch_str.encode('utf-8'))
    except Exception:
        root = None

    has_header = root is not None and bool(root.xpath('//header'))
    has_sheet  = root is not None and bool(root.xpath('//sheet'))

    if has_header:
        btn_xpath    = '//header'
        fields_xpath = '//header'
        fields_pos   = 'after'
    elif has_sheet:
        btn_xpath    = '//sheet'
        fields_xpath = '//sheet'
        fields_pos   = 'inside'
    else:
        btn_xpath    = '//form'
        fields_xpath = '//form'
        fields_pos   = 'inside'

    new_arch = f"""<data>
  <xpath expr="{btn_xpath}" position="inside">
    <button name="action_generate_and_reserve"
            string="Generate Numbers &amp; Reserve"
            type="object"
            class="btn-primary"
            attrs="{{'invisible': [('priority_number', '!=', '')]}}"/>
    <button name="action_create_reservation_manual"
            string="Create Reservation"
            type="object"
            attrs="{{'invisible': ['|', ('reservation_id', '!=', False), ('priority_number', '=', '')]}}"/>
  </xpath>
  <xpath expr="{fields_xpath}" position="{fields_pos}">
    <group string="Salaam City - Reference and Reservation">
      <group>
        <field name="priority_number" readonly="1" attrs="{{'invisible': [('priority_number', '=', '')]}}"/>
        <field name="file_number" readonly="1" attrs="{{'invisible': [('file_number', '=', '')]}}"/>
        <field name="property_id"/>
      </group>
      <group>
        <field name="reservation_id" readonly="1" attrs="{{'invisible': [('reservation_id', '=', False)]}}"/>
        <field name="reservation_state" readonly="1" attrs="{{'invisible': [('reservation_id', '=', False)]}}"/>
      </group>
    </group>
  </xpath>
</data>"""

    try:
        our_view.with_context(no_cow=True).write({
            'inherit_id': crm_form_view.id,
            'arch_db': new_arch,
        })
    except Exception:
        simple_arch = f"""<data>
  <xpath expr="{fields_xpath}" position="{fields_pos}">
    <group string="Salaam City - Reference">
      <field name="priority_number" readonly="1"/>
      <field name="file_number" readonly="1"/>
      <field name="property_id"/>
      <field name="reservation_id" readonly="1"/>
    </group>
  </xpath>
</data>"""
        try:
            our_view.with_context(no_cow=True).write({
                'inherit_id': crm_form_view.id,
                'arch_db': simple_arch,
            })
        except Exception:
            pass  # Never crash the install


def _fix_property_project_inherit(env):
    """Fix property.details project fields inherit view to point to real base view."""
    base_view = env['ir.ui.view'].search([
        ('model', '=', 'property.details'),
        ('type', '=', 'form'),
        ('mode', '=', 'base'),
        ('name', 'not like', 'fallback'),
    ], order='priority asc', limit=1)

    if not base_view:
        return

    our_view = env['ir.ui.view'].search([
        ('name', '=', 'property.details.salaam.project.inherit'),
    ], limit=1)

    if not our_view or our_view.inherit_id == base_view:
        return

    try:
        from lxml import etree
        arch_str = base_view.arch_db or base_view.arch
        root = etree.fromstring(arch_str.encode('utf-8'))
        has_price = bool(root.xpath('//field[@name="price"]'))
    except Exception:
        has_price = False

    if has_price:
        new_arch = """<data>
  <xpath expr="//field[@name='price']" position="after">
    <field name="salaam_project_id"/>
    <field name="salaam_sub_project_id"/>
  </xpath>
</data>"""
    else:
        new_arch = """<data>
  <xpath expr="//sheet" position="inside">
    <field name="salaam_project_id"/>
    <field name="salaam_sub_project_id"/>
  </xpath>
</data>"""

    try:
        our_view.with_context(no_cow=True).write({
            'inherit_id': base_view.id,
            'arch_db': new_arch,
        })
    except Exception:
        pass


# ─────────────────────────────────────────────────────────────────────────────
#  pre_init_hook  — runs BEFORE ORM creates/updates tables
# ─────────────────────────────────────────────────────────────────────────────

def pre_init_hook(env):
    cr = env.cr 
    """
    Pre-install hook:
    1. Drop stale FK constraints
    2. Drop old columns so they can be recreated
    3. Remove stale ir.model.fields entries that cause onchange errors

    IMPORTANT: Every ALTER TABLE statement is guarded by a table-existence
    check so that a fresh install (where salaam_reservation does not yet
    exist) does not crash with UndefinedTable.
    """

    # ── Always safe: remove stale ir.model.fields rows ───────────────────────
    # ir_model_fields always exists; the DELETE is a no-op if rows are absent.
    cr.execute("""
        DELETE FROM ir_model_fields
        WHERE model = 'salaam.reservation'
          AND name = 'pre_application_id'
    """)

    # ── Guard: only touch salaam_reservation if the table already exists ──────
    # On a FRESH INSTALL the table does not exist yet — Odoo creates it later.
    # On an UPGRADE it already exists and we can safely ALTER it.
    if not _table_exists(cr, 'salaam_reservation'):
        # Nothing more to do — ORM will create the table from scratch.
        return

    # ── Safe to ALTER from here — table confirmed to exist ───────────────────

    # Drop stale FK constraints (IF EXISTS makes these idempotent)
    cr.execute("""
        ALTER TABLE salaam_reservation
        DROP CONSTRAINT IF EXISTS salaam_reservation_crm_lead_id_fkey
    """)
    cr.execute("""
        ALTER TABLE salaam_reservation
        DROP CONSTRAINT IF EXISTS salaam_reservation_bre_application_id_fkey
    """)
    cr.execute("""
        ALTER TABLE salaam_reservation
        DROP CONSTRAINT IF EXISTS salaam_reservation_pre_application_id_fkey
    """)

    # Drop team_id column (Odoo will recreate with correct type)
    cr.execute("""
        ALTER TABLE salaam_reservation
        DROP COLUMN IF EXISTS team_id
    """)

    # Drop old Char project columns (recreated as Integer Many2one)
    cr.execute("""
        ALTER TABLE salaam_reservation
        DROP COLUMN IF EXISTS project_name,
        DROP COLUMN IF EXISTS sub_project_name
    """)
    cr.execute("""
        ALTER TABLE salaam_reservation
        DROP COLUMN IF EXISTS project_id,
        DROP COLUMN IF EXISTS sub_project_id
    """)


# ─────────────────────────────────────────────────────────────────────────────
#  post_init_hook  — runs AFTER ORM creates/updates tables
# ─────────────────────────────────────────────────────────────────────────────

def post_init_hook(env):
    """
    After installation:
    1. Fix property.details view inheritance to point to the real base view.
    2. Inject Salaam fields into the CRM lead form view.
    """
    # from odoo import api, SUPERUSER_ID
    # env = api.Environment(cr, SUPERUSER_ID, {})

    # Fix property.details inherit
    base_view = env['ir.ui.view'].search([
        ('model', '=', 'property.details'),
        ('type', '=', 'form'),
        ('mode', '=', 'base'),
        ('name', 'not like', 'fallback'),
    ], order='priority asc', limit=1)

    if not base_view:
        base_view = env['ir.ui.view'].search([
            ('model', '=', 'property.details'),
            ('type', '=', 'form'),
            ('name', 'not like', 'fallback'),
        ], order='priority asc', limit=1)

    if base_view:
        our_view = env['ir.ui.view'].search([
            ('name', '=', 'property.details.reservation.inherit'),
        ], limit=1)
        if our_view:
            our_view.write({'inherit_id': base_view.id})

    # Inject Salaam fields into CRM form view
    _inject_salaam_crm_fields(env)
    _fix_property_project_inherit(env)


# ─────────────────────────────────────────────────────────────────────────────
#  post_migrate  — runs on every upgrade
# ─────────────────────────────────────────────────────────────────────────────

def post_migrate(env):
    cr = env.cr
    """Re-apply CRM view injection on every module upgrade + fix FK constraints."""

    # Remove stale pre_application_id from ir.model.fields
    cr.execute("""
        DELETE FROM ir_model_fields
        WHERE model = 'salaam.reservation'
          AND name = 'pre_application_id'
    """)

    # Drop stale FK constraints (safe — IF EXISTS makes these idempotent)
    if _table_exists(cr, 'salaam_reservation'):
        cr.execute("""
            ALTER TABLE salaam_reservation
            DROP CONSTRAINT IF EXISTS salaam_reservation_crm_lead_id_fkey
        """)
        cr.execute("""
            ALTER TABLE salaam_reservation
            DROP CONSTRAINT IF EXISTS salaam_reservation_bre_application_id_fkey
        """)
        cr.execute("""
            ALTER TABLE salaam_reservation
            DROP CONSTRAINT IF EXISTS salaam_reservation_pre_application_id_fkey
        """)

    from odoo import api, SUPERUSER_ID
    env = api.Environment(cr, SUPERUSER_ID, {})
    _inject_salaam_crm_fields(env)
    _fix_property_project_inherit(env)
# def pre_init_hook(cr):
#     """
#     Pre-install hook:
#     1. Drop stale FK constraints
#     2. Drop old columns so they can be recreated
#     3. Remove stale ir.model.fields entries that cause onchange errors
#     """
#     # Remove stale pre_application_id from ir.model.fields — causes
#     # "Invalid field 'pre_application_id' on model 'salaam.reservation'"
#     cr.execute("""
#         DELETE FROM ir_model_fields
#         WHERE model = 'salaam.reservation'
#           AND name = 'pre_application_id';
#     """)
#     # Drop stale FK constraints
#     cr.execute("""
#         ALTER TABLE salaam_reservation
#         DROP CONSTRAINT IF EXISTS salaam_reservation_crm_lead_id_fkey;
#     """)
#     # Drop team_id if it exists (Odoo will recreate with correct type)
#     cr.execute("""
#         ALTER TABLE salaam_reservation
#         DROP COLUMN IF EXISTS team_id;
#     """)
#     # Drop stale FK on bre_application_id too (same issue)
#     cr.execute("""
#         ALTER TABLE salaam_reservation
#         DROP CONSTRAINT IF EXISTS salaam_reservation_bre_application_id_fkey;
#     """)
#     # Drop old Char project columns (recreated as Integer Many2one)
#     cr.execute("""
#         ALTER TABLE salaam_reservation
#         DROP COLUMN IF EXISTS project_name,
#         DROP COLUMN IF EXISTS sub_project_name;
#     """)
#     cr.execute("""
#         ALTER TABLE salaam_reservation
#         DROP COLUMN IF EXISTS project_id,
#         DROP COLUMN IF EXISTS sub_project_id;
#     """)
#
#
# # -*- coding: utf-8 -*-
# from . import models
#
#
# def _inject_salaam_crm_fields(env):
#     """
#     Directly inject Salaam Priority/File/Reservation fields into the real
#     CRM lead form view by patching the inherit view's parent to be the
#     actual CRM form, then force-writing a compatible arch.
#     Called from post_init_hook.
#     """
#     from lxml import etree
#
#     # Find the real CRM lead form view (lowest priority = main view)
#     crm_views = env['ir.ui.view'].search([
#         ('model', '=', 'crm.lead'),
#         ('type', '=', 'form'),
#         ('mode', '=', 'base'),
#     ], order='priority asc')
#
#     # Pick the one that is NOT our fallback
#     crm_form_view = None
#     for v in crm_views:
#         if 'fallback' not in (v.name or ''):
#             crm_form_view = v
#             break
#
#     if not crm_form_view:
#         return  # CRM not installed or no form view found
#
#     # Find our inherit view
#     our_view = env['ir.ui.view'].search([
#         ('name', '=', 'crm.lead.salaam.reservation.inherit'),
#     ], limit=1)
#
#     if not our_view:
#         return
#
#     # Get the real arch of the CRM form to discover what elements exist
#     try:
#         arch_str = crm_form_view.arch_db or crm_form_view.arch
#         root = etree.fromstring(arch_str.encode('utf-8'))
#     except Exception:
#         root = None
#
#     # Determine the best injection xpath based on what exists in the real view
#     # Try in order: //header, //sheet, //group[1], //form
#     has_header = root is not None and bool(root.xpath('//header'))
#     has_sheet = root is not None and bool(root.xpath('//sheet'))
#     has_group = root is not None and bool(root.xpath('//group'))
#
#     if has_header:
#         btn_xpath = '//header'
#         fields_xpath = '//header'
#         fields_pos = 'after'
#     elif has_sheet:
#         btn_xpath = '//sheet'
#         fields_xpath = '//sheet'
#         fields_pos = 'inside'
#     elif has_group:
#         btn_xpath = '//group[1]'
#         fields_xpath = '//group[1]'
#         fields_pos = 'before'
#     else:
#         btn_xpath = '//form'
#         fields_xpath = '//form'
#         fields_pos = 'inside'
#
#     # Build the new arch for our inherit view
#     new_arch = f"""<data>
#   <xpath expr="{btn_xpath}" position="inside">
#     <button name="action_generate_and_reserve"
#             string="Generate Numbers &amp; Reserve"
#             type="object"
#             class="btn-primary"
#             attrs="{{'invisible': [('priority_number', '!=', '')]}}"/>
#     <button name="action_create_reservation_manual"
#             string="Create Reservation"
#             type="object"
#             attrs="{{'invisible': ['|', ('reservation_id', '!=', False), ('priority_number', '=', '')]}}"/>
#   </xpath>
#   <xpath expr="{fields_xpath}" position="{fields_pos}">
#     <group string="Salaam City - Reference and Reservation">
#       <group>
#         <field name="priority_number" readonly="1" attrs="{{'invisible': [('priority_number', '=', '')]}}"/>
#         <field name="file_number" readonly="1" attrs="{{'invisible': [('file_number', '=', '')]}}"/>
#         <field name="property_id"/>
#       </group>
#       <group>
#         <field name="reservation_id" readonly="1" attrs="{{'invisible': [('reservation_id', '=', False)]}}"/>
#         <field name="reservation_state" readonly="1" attrs="{{'invisible': [('reservation_id', '=', False)]}}"/>
#       </group>
#     </group>
#   </xpath>
# </data>"""
#
#     try:
#         our_view.with_context(no_cow=True).write({
#             'inherit_id': crm_form_view.id,
#             'arch_db': new_arch,
#         })
#     except Exception as e:
#         # If arch validation fails, try a simpler arch with just the fields group
#         simple_arch = f"""<data>
#   <xpath expr="{fields_xpath}" position="{fields_pos}">
#     <group string="Salaam City - Reference">
#       <field name="priority_number" readonly="1"/>
#       <field name="file_number" readonly="1"/>
#       <field name="property_id"/>
#       <field name="reservation_id" readonly="1"/>
#     </group>
#   </xpath>
# </data>"""
#         try:
#             our_view.with_context(no_cow=True).write({
#                 'inherit_id': crm_form_view.id,
#                 'arch_db': simple_arch,
#             })
#         except Exception:
#             pass  # Never crash the install
#
#
#
# def post_init_hook(cr, registry):
#     """
#     After installation, fix property.details view inheritance:
#     1. Find the actual base form view for property.details from rental_management
#     2. Update our inherit view to inherit from it instead of our fallback
#     3. Optionally delete the fallback view (it has priority=999 so it won't interfere)
#     """
#     from odoo import api, SUPERUSER_ID
#     env = api.Environment(cr, SUPERUSER_ID, {})
#
#     # Find the REAL base form view (from rental_management or similar)
#     # Exclude our own fallback view
#     base_view = env['ir.ui.view'].search([
#         ('model', '=', 'property.details'),
#         ('type', '=', 'form'),
#         ('mode', '=', 'base'),
#         ('name', 'not like', 'fallback'),
#     ], order='priority asc', limit=1)
#
#     if not base_view:
#         base_view = env['ir.ui.view'].search([
#             ('model', '=', 'property.details'),
#             ('type', '=', 'form'),
#             ('name', 'not like', 'fallback'),
#         ], order='priority asc', limit=1)
#
#     if base_view:
#         our_view = env['ir.ui.view'].search([
#             ('name', '=', 'property.details.reservation.inherit'),
#         ], limit=1)
#         if our_view:
#             our_view.write({'inherit_id': base_view.id})
#
#     # ── Inject Salaam fields directly into the real CRM form view arch ───────
#     # This approach directly modifies the combined arch of the real CRM view
#     # rather than relying on a fragile inherit chain. Works regardless of
#     # how heavily the CRM form has been customised.
#     _inject_salaam_crm_fields(env)
#     _fix_property_project_inherit(env)
#
#
# def _fix_property_project_inherit(env):
#     """Fix property.details project fields inherit view to point to real base view."""
#     base_view = env['ir.ui.view'].search([
#         ('model', '=', 'property.details'),
#         ('type', '=', 'form'),
#         ('mode', '=', 'base'),
#         ('name', 'not like', 'fallback'),
#     ], order='priority asc', limit=1)
#     if not base_view:
#         return
#     our_view = env['ir.ui.view'].search([
#         ('name', '=', 'property.details.salaam.project.inherit'),
#     ], limit=1)
#     if our_view and our_view.inherit_id != base_view:
#         # Rebuild arch using price field if it exists, else use sheet
#         try:
#             from lxml import etree
#             arch_str = base_view.arch_db or base_view.arch
#             root = etree.fromstring(arch_str.encode('utf-8'))
#             has_price = bool(root.xpath('//field[@name="price"]'))
#         except Exception:
#             has_price = False
#
#         if has_price:
#             new_arch = """<data>
#   <xpath expr="//field[@name='price']" position="after">
#     <field name="salaam_project_id"/>
#     <field name="salaam_sub_project_id"/>
#   </xpath>
# </data>"""
#         else:
#             new_arch = """<data>
#   <xpath expr="//sheet" position="inside">
#     <field name="salaam_project_id"/>
#     <field name="salaam_sub_project_id"/>
#   </xpath>
# </data>"""
#         try:
#             our_view.with_context(no_cow=True).write({
#                 'inherit_id': base_view.id,
#                 'arch_db': new_arch,
#             })
#         except Exception:
#             pass
#
# def post_migrate(cr, registry):
#     """Re-apply CRM view injection on every module upgrade + fix FK constraints."""
#     # Remove stale pre_application_id from ir.model.fields
#     cr.execute("""
#         DELETE FROM ir_model_fields
#         WHERE model = 'salaam.reservation'
#           AND name = 'pre_application_id';
#     """)
#     # Drop stale FK constraints (safe to run every upgrade)
#     cr.execute("""
#         ALTER TABLE salaam_reservation
#         DROP CONSTRAINT IF EXISTS salaam_reservation_crm_lead_id_fkey;
#     """)
#     cr.execute("""
#         ALTER TABLE salaam_reservation
#         DROP CONSTRAINT IF EXISTS salaam_reservation_bre_application_id_fkey;
#     """)
#     cr.execute("""
#         ALTER TABLE salaam_reservation
#         DROP CONSTRAINT IF EXISTS salaam_reservation_pre_application_id_fkey;
#     """)
#     from odoo import api, SUPERUSER_ID
#     env = api.Environment(cr, SUPERUSER_ID, {})
#     _inject_salaam_crm_fields(env)
#     _fix_property_project_inherit(env)
#
